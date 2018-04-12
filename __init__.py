import time
import docker
import sys
import progress.bar


class Service():

    def __init__(self, service):
        self._service = service

    @property
    def name(self):
        return self._service.name

    def update(self):
        self._service.reload()

    def get_state(self):
        if 'UpdateStatus' in self._service.attrs:
            return "{} ({})".format(self._service.attrs['UpdateStatus']['State'], self._service.attrs['UpdateStatus']['Message'])
        else:
            return "No Update In Progress"

    def is_complete(self):
        if 'UpdateStatus' not in self._service.attrs:
            return True
        elif self._service.attrs['UpdateStatus']['State'] in ['completed', 'paused']:
            return True
        else:
            return False

    @property
    def success(self):
        return 'UpdateStatus' not in self._service.attrs or self._service.attrs['UpdateStatus']['State'] in ['completed']


def main(stack_name):
    client = docker.from_env()
    services = [
        Service(x) for x in client.services.list() if x.name.startswith(stack_name + "_")
    ]

    bar = progress.bar.Bar("Deploying", max=len(services))

    while True:
        for s in services:
            s.update()

        bar.index = len(list(filter(lambda x: x.is_complete(), services)))
        bar.update()

        if all([s.is_complete() for s in services]):
            self.finish()
            for s in services:
                print("{} - {}".format(s.name, s.get_state()))

            if all([s.success for s in services]):
                exit(0)
            else:
                exit(1)

        time.sleep(1)

main(sys.argv[1])
