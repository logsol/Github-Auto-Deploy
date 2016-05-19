#!/usr/bin/env python

import json, urlparse, sys, os
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from subprocess import call
import argparse


__version__ = '0.2'


DEFAULT_CONFIG_FILEPATH = './GitAutoDeploy.conf.json'


class GitAutoDeploy(BaseHTTPRequestHandler):
    _config = None
    quiet = False
    daemon = False

    @classmethod
    def init_config(cls, path):
        try:
            configString = open(path).read()
        except:
            sys.exit('Could not load ' + path + ' file')

        try:
            cls._config = json.loads(configString)
        except:
            sys.exit(path + ' file is not valid json')

        for repository in cls.config['repositories']:
            if(not os.path.isdir(repository['path'])):
                sys.exit('Directory ' + repository['path'] + ' not found')
            # Check for a repository with a local or a remote GIT_WORK_DIR
            if not os.path.isdir(os.path.join(repository['path'], '.git')) \
               and not os.path.isdir(os.path.join(repository['path'], 'objects')):
                sys.exit('Directory ' + repository['path'] + ' is not a Git repository')

    @property
    def config(self):
        if self._config is None:
            raise Exception('Config not initialized')
        else:
            return self._config

    def do_POST(self):
        event = self.headers.getheader('X-Github-Event')
        if event == 'ping':
            if not self.quiet:
                print 'Ping event received'
            self.respond(204)
            return
        if event != 'push':
            if not self.quiet:
                print 'We only handle ping and push events'
            self.respond(304)
            return

        self.respond(204)

        urls = self.parseRequest()
        for url in urls:
            paths = self.getMatchingPaths(url)
            for path in paths:
                self.fetch(path)
                self.deploy(path)

    def parseRequest(self):
        length = int(self.headers.getheader('content-length'))
        body = self.rfile.read(length)
        payload = json.loads(body)
        self.branch = payload['ref']
        return [payload['repository']['url']]

    def getMatchingPaths(self, repoUrl):
        res = []
        for repository in self.config['repositories']:
            if(repository['url'] == repoUrl):
                res.append(repository['path'])
        return res

    def respond(self, code):
        self.send_response(code)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()

    def fetch(self, path):
        if(not self.quiet):
            print "\nPost push request received"
            print 'Updating ' + path
        call(['cd "' + path + '" && git fetch'], shell=True)

    def deploy(self, path):
        for repository in self.config['repositories']:
            if(repository['path'] == path):
                if 'deploy' in repository:
                    branch = None
                    if 'branch' in repository:
                        branch = repository['branch']

                    if branch is None or branch == self.branch:
                        if(not self.quiet):
                            print 'Executing deploy command'
                        call(['cd "' + path + '" && ' + repository['deploy']], shell=True)

                    elif not self.quiet:
                        print 'Push to different branch (%s != %s), not deploying' % (branch, self.branch)
                break


def get_args():
    parser = argparse.ArgumentParser(description='Github Autodeploy Service')
    parser.add_argument('-q', '--quiet', action='store_true', help='disable status reporting')
    parser.add_argument('-d', '--daemon-mode', action='store_true', help='run this script as a daemon')
    parser.add_argument('-c', '--config', default=GitAutoDeploy.DEFAULT_CONFIG_FILEPATH,
                        help='provide an alternative path for the config file used')

    return parser.parse_args()


def main():
    server = None
    try:
        args = get_args()

        GitAutoDeploy.quiet = args.quiet or args.daemon_mode
        GitAutoDeploy.daemon = args.daemon_mode
        GitAutoDeploy.init_config(args.config)

        if(GitAutoDeploy.daemon):
            pid = os.fork()
            if(pid != 0):
                sys.exit()
            os.setsid()

        if(not GitAutoDeploy.quiet):
            if not GitAutoDeploy.daemon:
                print 'Github Autodeploy Service v' + __version__ + ' started'
            else:
                print 'Github Autodeploy Service v' + __version__ + ' started in daemon mode'

        server = HTTPServer(('', GitAutoDeploy._config['port']), GitAutoDeploy)
        server.serve_forever()
    except (KeyboardInterrupt, SystemExit) as e:
        if(e): # wtf, why is this creating a new line?
            print >> sys.stderr, e

        if(not server is None):
            server.socket.close()

        if(not GitAutoDeploy.quiet):
            print 'Goodbye'

if __name__ == '__main__':
     main()
