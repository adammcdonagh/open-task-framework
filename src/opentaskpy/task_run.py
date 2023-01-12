import os
import sys
import datetime
import json
from opentaskpy.config.schemas import validate_json
from glob import glob
from opentaskpy.taskhandlers.transfer import Transfer
import logging
import importlib
import jinja2
from jinja2 import Template

GLOBAL_VARIABLES = dict()
GLOBAL_VERBOSITY = 1
MAX_DEPTH = 5


class TaskRun:

    # Return global variables
    def get_global_variables(self):
        return GLOBAL_VARIABLES

    def delta_days(self, value, days):
        return value + datetime.timedelta(days)

    def template_lookup(self, plugin, **kwargs):
        self.logger.log(11, f"Got call to lookup function {plugin} with kwargs {kwargs}")

        # Import the plugin if its not already loaded
        if f"opentaskpy.plugins.lookup.{plugin}" not in sys.modules:
            # Check the module is loadable
            try:
                importlib.import_module(f"opentaskpy.plugins.lookup.{plugin}")
            except ModuleNotFoundError:
                self.logger.log(
                    11, f"Module not found: opentaskpy.plugins.lookup.{plugin}. Looking in plugins directory instead"
                )
                pass

        # If we haven't loaded the plugin yet, then look in the cfg/plugins directory and see if we can find it
        if f"opentaskpy.plugins.lookup.{plugin}" not in sys.modules:
            plugin_path = f"{self.config_dir}/plugins/{plugin}.py"
            if os.path.isfile(plugin_path):
                spec = importlib.util.spec_from_file_location(f"opentaskpy.plugins.lookup.{plugin}", plugin_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                sys.modules[f"opentaskpy.plugins.lookup.{plugin}"] = module

        # Run the run function of the imported module
        return getattr(sys.modules[f"opentaskpy.plugins.lookup.{plugin}"], "run")(**kwargs)

    def load_global_variables(self):
        global GLOBAL_VARIABLES
        global_variables = dict()
        variable_configs = []
        file_types = (".json.j2", ".json")
        for file_type in file_types:
            variable_configs.extend(glob(f"{self.config_dir}/**/variables{file_type}", recursive=True))
        if not variable_configs:
            # self.logger.error("Couldn't find any variables.(json|json.j2) files")
            raise FileNotFoundError("Couldn't find any variables.(json|json.j2) files")
        else:
            for variable_file in variable_configs:
                with open(variable_file) as json_file:
                    this_variable_config = json.load(json_file)
                    global_variables = global_variables | this_variable_config

        GLOBAL_VARIABLES = global_variables

    def resolve_templated_variables(self):

        global GLOBAL_VARIABLES
        # We need to evaluate the variables themselves, incase theres any recursion
        # Convert the variables to a JSON string which we can process with the jinja2 templater
        global MAX_DEPTH
        current_depth = 0
        previous_render = None

        variables_template = self.template_env.from_string(json.dumps(GLOBAL_VARIABLES))
        variables_template.globals["now"] = datetime.datetime.utcnow

        # Define lookup function
        variables_template.globals["lookup"] = self.template_lookup

        evaluated_variables = variables_template.render(GLOBAL_VARIABLES)

        while evaluated_variables != previous_render and current_depth < MAX_DEPTH:
            previous_render = evaluated_variables

            variables_template = self.template_env.from_string(evaluated_variables)
            evaluated_variables = variables_template.render(json.loads(evaluated_variables))

            current_depth += 1
            if current_depth >= MAX_DEPTH:
                self.logger.error(
                    "Reached max depth of recursive template evaluation. Please check the task as variable definitions for infinite recursion"
                )
                raise Exception("Reached max depth of recursive template evaluation")

        GLOBAL_VARIABLES = json.loads(evaluated_variables)

    def load_task_definition(self, task_definition_file):
        global GLOBAL_VARIABLES
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
                GLOBAL_VARIABLES = GLOBAL_VARIABLES | task_definition["variables"]

            template = self.template_env.from_string(json_content)
            rendered_template = template.render(GLOBAL_VARIABLES)
            active_task_definition = json.loads(rendered_template)
            self.logger.log(12, f"Evalated task definition: {json.dumps(active_task_definition)}")

        return active_task_definition

    def __init__(self, task_id, config_dir):
        self.logger = logging.getLogger(__name__)
        self.task_id = task_id
        self.config_dir = config_dir
        self.active_task_definition = None
        self.template_env = None

        # Force Jinja2 to log undefined variables
        jinja2.make_logging_undefined(logger=self.logger, base=jinja2.Undefined)  # noqa
        self.template_env = jinja2.Environment(undefined=jinja2.StrictUndefined)
        self.template_env.filters["delta_days"] = self.delta_days

    def run(self):
        self.logger.log(12, f"Looking in {self.config_dir}")

        # Load global config variables
        self.load_global_variables()

        # Load configuration for given task
        json_config = glob(f"{self.config_dir}/**/{self.task_id}.json", recursive=True)
        if not json_config or len(json_config) != 1:
            self.logger.error(f"Couldn't find task with name: {self.task_id}")
            raise FileNotFoundError

        found_file = json_config[0]
        self.logger.log(12, f"Found: {found_file}")

        # Resolve any templated variables in the global variables
        self.resolve_templated_variables()
        global GLOBAL_VARIABLES

        # Populate the task definition with the global variables
        active_task_definition = self.load_task_definition(found_file)

        # Now we've loaded the config, determine what to do with it
        if "type" not in active_task_definition:
            self.logger.error("Invalid task configuration. Cannot continue")
            return False
        elif active_task_definition["type"] == "transfer":
            # Hand off to the transfer module
            self.logger.log(12, "Transfer")
            # Validate the schema
            if not validate_json(active_task_definition):
                self.logger.error("JSON format does not match schema")
                return False

            transfer = Transfer(self.task_id, active_task_definition)

            return transfer.run()

        elif active_task_definition["type"] == "execution":
            # Hand off to the execuiton module
            self.logger.log(12, "Execution")
            raise NotImplementedError
        elif active_task_definition["type"] == "batch":
            # Hand off to the batch module
            self.logger.log(12, "Batch")
            raise NotImplementedError

        else:
            self.logger.error("Unknown task type!")
            return False
