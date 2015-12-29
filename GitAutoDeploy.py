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
    def getConfig(myClass):
        if(myClass.config == None):
            try:
                configString = open(myClass.CONFIG_FILEPATH).read()
            except:
                sys.exit('Could not load ' + myClass.CONFIG_FILEPATH + ' file')

            try:
                myClass.config = json.loads(configString)
            except:
                sys.exit(myClass.CONFIG_FILEPATH + ' file is not valid json')

            for repository in myClass.config['repositories']:
                if(not os.path.isdir(repository['path'])):
                    sys.exit('Directory ' + repository['path'] + ' not found')
                # Check for a repository with a local or a remote GIT_WORK_DIR
                if not os.path.isdir(os.path.join(repository['path'], '.git')) \
                   and not os.path.isdir(os.path.join(repository['path'], 'objects')):
                    sys.exit('Directory ' + repository['path'] + ' is not a Git repository')

        return myClass.config

    def do_POST(self):
        isValid = False

        agent = self.headers.getheader("User-Agent")

        # print User-Agent, helps to diagnose, bitbucket should be "Bitbucket-Webhooks/2.0"
        if not self.quiet:
            print "User Agent is: ", agent

        if agent == "Bitbucket-Webhooks/2.0":
            isValid = self.processBitBucketRequest()
        else:
            isValid = self.processGithubRequest()


        for url in self.urls:
            paths = self.getMatchingPaths(url)
            for path in paths:
                self.fetch(path)
                self.deploy(path)

    def processGithubRequest(self):
        self.event = self.headers.getheader('X-Github-Event')
        if not self.quiet:
            print "Recieved event", self.event

        if self.event == 'ping':
            if not self.quiet:
                print 'Ping event received'
            self.respond(204)
            return False
        if self.event != 'push':
            if not self.quiet:
                print 'We only handle ping and push events'
            self.respond(304)
            return False

        self.respond(204)

        length = int(self.headers.getheader('content-length'))
        body = self.rfile.read(length)
        payload = json.loads(body)
        self.branch = payload['ref']
        self.urls = [payload['repository']['url']]
        return True

    def processBitBucketRequest(self):
        self.event = self.headers.getheader('X-Event-Key')
        if not self.quiet:
            print "Recieved event", self.event

        if self.event != 'repo:push':
            if not self.quiet:
                print 'We only handle ping and push events'
            self.respond(304)
            return False

        length = int(self.headers.getheader('content-length'))
        body = self.rfile.read(length)
        self.respond(204)
        payload = json.loads(body)
        self.branch = payload['push']['changes'][0]['new']['name']
        self.urls = [payload['repository']['links']['html']['href']]

        return True


    def getMatchingPaths(self, repoUrl):
        res = []
        config = self.getConfig()
        for repository in config['repositories']:
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
        config = self.getConfig()
        for repository in config['repositories']:
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

def main():
    try:
        server = None
        for arg in sys.argv:
            if(arg == '-d' or arg == '--daemon-mode'):
                GitAutoDeploy.daemon = True
                GitAutoDeploy.quiet = True
            if(arg == '-q' or arg == '--quiet'):
                GitAutoDeploy.quiet = True

        if(GitAutoDeploy.daemon):
            pid = os.fork()
            if(pid != 0):
                sys.exit()
            os.setsid()

        if(not GitAutoDeploy.quiet):
            print 'Github Autodeploy Service v0.2 started'
        else:
            print 'Github Autodeploy Service v 0.2 started in daemon mode'

        server = HTTPServer(('', GitAutoDeploy.getConfig()['port']), GitAutoDeploy)
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
