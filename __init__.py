import time
import docker
import sys
import subprocess
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

    # Docker Python API doesn't seem to support listing services and stacks, so we have to do
    # some nasty shell parsing

    try:
        output = subprocess.check_output([
            '/usr/bin/docker',
            'stack', 'list',
            '--format', '{{.Name}}'
        ])
    except subprocess.CalledProcessError:
        print("Cannot list stacks")
        print(output)
        exit(1)

    if stack_name not in output.decode('utf-8').split('\n'):
        print("Stack {} not found".format(stack_name))

    try:
        output = subprocess.check_output([
            '/usr/bin/docker',
            'stack', 'services', stack_name,
            '--format', '{{.Name}}'
        ])
    except subprocess.CalledProcessError:
        print("Cannot find services for stack {}".format(stack_name))
        print(output)
        exit(1)

    service_names = output.decode('utf-8').split('\n')

    services = [
        Service(x) for x in client.services.list() if x.name in service_names
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
