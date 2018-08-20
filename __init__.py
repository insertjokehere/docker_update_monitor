import time
import docker
import sys
import progress.bar


class Service():

    def __init__(self, service):
        self._service = service
        # If the service has a 'monitor_hint' label of 'oneshot', then instead of waiting for the update state
        # to be OK, we should wait for the container to exit with status of 0
        self._oneshot_mode = self._service.attrs['Spec'].get('Labels', {}).get('monitor_hint', '') == 'oneshot'

    @property
    def name(self):
        return self._service.name

    def update(self):
        self._service.reload()

    def get_state(self):
        if self._oneshot_mode:
            task = self._service.tasks()[0]
            state = task['Status']['State']
            if 'Err' in task['Status']:
                state += " ({})".format(task['Status']['Err'])
            return state
        else:
            if 'UpdateStatus' in self._service.attrs:
                return "{} ({})".format(self._service.attrs['UpdateStatus']['State'], self._service.attrs['UpdateStatus']['Message'])
            else:
                return "No Update In Progress"

    def is_complete(self):
        if self._oneshot_mode:
            return self._service.tasks()[0]['DesiredState'] == 'shutdown'
        elif 'UpdateStatus' not in self._service.attrs:
            return True
        elif self._service.attrs['UpdateStatus']['State'] in ['completed', 'paused']:
            return True
        else:
            return False

    @property
    def success(self):
        if self._oneshot_mode:
            task = self._service.tasks()[0]
            return 'ContainerStatus' in task['Status'] and \
                'ExitCode' in task['Status']['ContainerStatus'] and \
                task['Status']['ContainerStatus']['ExitCode'] == 0
        else:
            return 'UpdateStatus' not in self._service.attrs or self._service.attrs['UpdateStatus']['State'] in ['completed']


def main(stack_name):
    client = docker.from_env()

    # TODO: Fetch stack members via docker API
    services = [
        Service(x) for x in client.services.list() if x.name.startswith(stack_name + "_") or x.name == stack_name
    ]

    bar = progress.bar.Bar("Deploying", max=len(services))

    while True:
        for s in services:
            s.update()

        bar.index = len(list(filter(lambda x: x.is_complete(), services)))
        bar.update()

        if all([s.is_complete() for s in services]):
            bar.finish()
            for s in services:
                print("{} - {}".format(s.name, s.get_state()))

            if all([s.success for s in services]):
                exit(0)
            else:
                exit(1)

        time.sleep(1)

main(sys.argv[1])
