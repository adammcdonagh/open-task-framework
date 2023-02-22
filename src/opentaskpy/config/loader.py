import datetime
import importlib
import json
import os
import sys
from glob import glob

import jinja2
from jinja2 import Template

import opentaskpy.logging
from opentaskpy.exceptions import DuplicateConfigFileError

MAX_DEPTH = 5


class ConfigLoader:
    def __init__(self, config_dir):
        self.logger = opentaskpy.logging.init_logging(__name__)
        self.config_dir = config_dir
        self.template_env = None
        self.global_variables = dict()

        self.logger.log(12, f"Looking in {self.config_dir}")

        # Force Jinja2 to log undefined variables
        jinja2.make_logging_undefined(logger=self.logger, base=jinja2.Undefined)  # noqa
        self.template_env = jinja2.Environment(undefined=jinja2.StrictUndefined)
        self.template_env.filters["delta_days"] = self.delta_days

        self._load_global_variables()
        self._resolve_templated_variables()

    def get_global_variables(self):
        return self.global_variables

    def delta_days(self, value, days):
        return value + datetime.timedelta(days)

    def template_lookup(self, plugin, **kwargs):
        self.logger.log(
            11, f"Got call to lookup function {plugin} with kwargs {kwargs}"
        )

        # Append the globals to the kwargs
        kwargs["globals"] = self.global_variables

        # Import the plugin if its not already loaded
        if f"opentaskpy.plugins.lookup.{plugin}" not in sys.modules:
            # Check the module is loadable
            try:
                importlib.import_module(f"opentaskpy.plugins.lookup.{plugin}")
            except ModuleNotFoundError:
                self.logger.log(
                    11,
                    f"Module not found: opentaskpy.plugins.lookup.{plugin}. Looking in plugins directory instead",
                )
                pass

        # If we haven't loaded the plugin yet, then look in the cfg/plugins directory and see if we can find it
        if f"opentaskpy.plugins.lookup.{plugin}" not in sys.modules:
            plugin_path = f"{self.config_dir}/plugins/{plugin}.py"
            if os.path.isfile(plugin_path):
                spec = importlib.util.spec_from_file_location(
                    f"opentaskpy.plugins.lookup.{plugin}", plugin_path
                )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                sys.modules[f"opentaskpy.plugins.lookup.{plugin}"] = module

        # Run the run function of the imported module
        return getattr(  # noqa: B009
            sys.modules[f"opentaskpy.plugins.lookup.{plugin}"], "run"
        )(**kwargs)

    # TASK DEFINITION FIND FILE
    def load_task_definition(self, task_id):
        json_config = glob(f"{self.config_dir}/**/{task_id}.json", recursive=True)
        if not json_config or len(json_config) != 1:
            if len(json_config) > 1:
                raise DuplicateConfigFileError(
                    f"Found more than one task with name: {task_id}"
                )

            raise FileNotFoundError(f"Couldn't find task with name: {task_id}")

        found_file = json_config[0]
        self.logger.log(12, f"Found: {found_file}")

        return self._enrich_variables(found_file)

    # POPULATE VARIABLES INSIDE TASK DEFINITION
    # AND LOAD ADDITIONAL VARIABLES FROM TASK DEFINITION
    def _enrich_variables(self, task_definition_file):
        active_task_definition = None
        with open(task_definition_file) as json_file:
            json_content = json_file.read()
            template = Template(json_content)
            # Render the template without evaluating any variables yet
            rendered_template = template.render()

            # From this, convert it to JSON and pull out the variables key if there is one
            task_definition = json.loads(rendered_template)
            # Extend or replace any local variables for this task
            if "variables" in task_definition:
                self.global_variables = (
                    self.global_variables | task_definition["variables"]
                )

            template = self.template_env.from_string(json_content)
            rendered_template = template.render(self.global_variables)
            active_task_definition = json.loads(rendered_template)
            self.logger.log(
                12, f"Evaluated task definition: {json.dumps(active_task_definition)}"
            )

        return active_task_definition

    # READ AND PARSE ACTUAL VARIABLE FILES
    def _load_global_variables(self):
        global_variables = dict()
        variable_configs = []
        file_types = (".json.j2", ".json")
        for file_type in file_types:
            variable_configs.extend(
                glob(f"{self.config_dir}/**/variables{file_type}", recursive=True)
            )
        if not variable_configs:
            # self.logger.error("Couldn't find any variables.(json|json.j2) files")
            raise FileNotFoundError(
                f"Couldn't find any variables.(json|json.j2) files under {self.config_dir}"
            )
        else:
            for variable_file in variable_configs:
                with open(variable_file) as json_file:
                    this_variable_config = json.load(json_file)
                    global_variables = global_variables | this_variable_config

        self.global_variables = global_variables

    # RESOLVE ANY VARIABLES THAT USE OTHER VARIABLES IN THE VARIABLE FILES
    def _resolve_templated_variables(self):
        # We need to evaluate the variables themselves, incase theres any recursion
        # Convert the variables to a JSON string which we can process with the jinja2 templater
        global MAX_DEPTH
        current_depth = 0
        previous_render = None

        variables_template = self.template_env.from_string(
            json.dumps(self.global_variables)
        )
        variables_template.globals["now"] = datetime.datetime.utcnow

        # Define lookup function
        variables_template.globals["lookup"] = self.template_lookup

        evaluated_variables = variables_template.render(self.global_variables)

        while evaluated_variables != previous_render and current_depth < MAX_DEPTH:
            previous_render = evaluated_variables

            variables_template = self.template_env.from_string(evaluated_variables)
            evaluated_variables = variables_template.render(
                json.loads(evaluated_variables)
            )

            current_depth += 1
            if current_depth >= MAX_DEPTH:
                self.logger.error(
                    "Reached max depth of recursive template evaluation. Please check the task as variable definitions for infinite recursion"
                )
                raise Exception("Reached max depth of recursive template evaluation")

        self.global_variables = json.loads(evaluated_variables)
