# OTF Task Types

As mentioned in the [README.md](../README.md), there are 3 types of tasks

## **Transfers**
As the name suggests, these are just file transfers from a source system, to 1 or more destinations.
At present, this only supports transfer via SFTP/SSH, but in future the plan is to add S3 capabilities too.

In addition to a simple file transfer, transfers can poll for files, watch the contents of log files, only collect files based on age and size, and carry out post copy actions (archive or delete source file) once the transfer has completed.

## **Executions**
Again, fairly obvious, this will run commands on one or more remote hosts via SSH.

## **Batches**
A batch is a combination of the above 2 task types, and other batches too.

Batches can have dependencies between tasks, timeouts, and failure recovery e.g. rerunning from the last point of failure