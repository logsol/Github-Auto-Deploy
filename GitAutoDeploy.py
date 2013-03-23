#!/usr/bin/env python

import json, urlparse, sys, os
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from subprocess import call


class GitAutoDeploy(BaseHTTPRequestHandler):
    CONFIG_FILEPATH = './GitAutoDeploy.conf.json'
    config = None
    quiet = False
    daemon = False

    @classmethod
    def getConfig(cls):
        if cls.config is None:
            try:
                configString = open(cls.CONFIG_FILEPATH).read()
            except IOError:
                sys.exit('Could not load ' + cls.CONFIG_FILEPATH + ' file')

            try:
                cls.config = json.loads(configString)
            except:
                sys.exit(cls.CONFIG_FILEPATH + ' file is not valid json')

            for repository in cls.config['repositories']:
                if not os.path.isdir(repository['path']):
                    sys.exit('Directory ' + repository['path'] + ' not found')
                if not os.path.isdir(repository['path'] + '/.git'):
                    sys.exit('Directory ' + repository['path'] + ' is not a Git repository')

        return cls.config

    def do_POST(self):
        urls = self.parseRequest()
        for url in urls:
            paths = self.getMatchingPaths(url)
            for path in paths:
                self.pull(path)
                self.deploy(path)

    def parseRequest(self):
        length = int(self.headers.getheader('content-length'))
        body = self.rfile.read(length)
        post = urlparse.parse_qs(body)
        items = []
        for itemString in post['payload']:
            item = json.loads(itemString)
            items.append(item['repository']['url'])
        return items

    def getMatchingPaths(self, repoUrl):
        res = []
        config = self.getConfig()
        for repository in config['repositories']:
            if repository['url'] == repoUrl:
                res.append(repository['path'])
        return res

    def respond(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()

    def pull(self, path):
        if not self.quiet:
            print "\nPost push request received"
            print 'Updating ' + path
        call(['cd "' + path + '" && git pull'], shell=True)

    def deploy(self, path):
        config = self.getConfig()
        for repository in config['repositories']:
            if repository['path'] == path:
                if 'deploy' in repository:
                    if not self.quiet:
                        print 'Executing deploy command'
                    call(['cd "' + path + '" && ' + repository['deploy']], shell=True)
                break


def main():
    global server
    try:
        server = None
        for arg in sys.argv:
            if arg == '-d' or arg == '--daemon-mode':
                GitAutoDeploy.daemon = True
                GitAutoDeploy.quiet = True
            if arg == '-q' or arg == '--quiet':
                GitAutoDeploy.quiet = True

        if GitAutoDeploy.daemon:
            pid = os.fork()
            if pid != 0:
                sys.exit()
            os.setsid()

        if not GitAutoDeploy.quiet:
            print 'Github Autodeploy Service v 0.1 started'
        else:
            print 'Github Autodeploy Service v 0.1 started in daemon mode'

        server = HTTPServer(('', GitAutoDeploy.getConfig()['port']), GitAutoDeploy)
        server.serve_forever()
    except (KeyboardInterrupt, SystemExit) as e:
        if e:  # wtf, why is this creating a new line?
            print >> sys.stderr, e

        if not server is None:
            server.socket.close()

        if not GitAutoDeploy.quiet:
            print 'Goodbye'


if __name__ == '__main__':
    main()
