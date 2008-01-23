##
## func command line interface & client lib
##
## Copyright 2007, Red Hat, Inc
## Michael DeHaan <mdehaan@redhat.com>
## +AUTHORS
##
## This software may be freely redistributed under the terms of the GNU
## general public license.
##
## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
##

import sys
import glob

from func.commonconfig import CMConfig
from func.config import read_config, CONFIG_FILE

import sslclient

import command
import forkbomb
import groups
import jobthing


# ===================================
# defaults
# TO DO: some of this may want to come from config later

DEFAULT_PORT = 51234
FUNC_USAGE = "Usage: %s [ --help ] [ --verbose ] target.example.org module method arg1 [...]"

# ===================================

class CommandAutomagic(object):
    """
    This allows a client object to act as if it were one machine, when in
    reality it represents many.
    """

    def __init__(self, clientref, base, nforks=1):
        self.base = base
        self.clientref = clientref
        self.nforks = nforks

    def __getattr__(self,name):
        base2 = self.base[:]
        base2.append(name)
        return CommandAutomagic(self.clientref, base2, self.nforks)

    def __call__(self, *args):
        if not self.base:
            raise AttributeError("something wrong here")
        if len(self.base) < 2:
            raise AttributeError("no method called: %s" % ".".join(self.base))
        module = self.base[0]
        method = ".".join(self.base[1:])
        return self.clientref.run(module,method,args,nforks=self.nforks)


# ===================================
# this is a module level def so we can use it and isServer() from
# other modules with a Client class
def expand_servers(spec, port=51234, noglobs=None, verbose=None, just_fqdns=False):
    """
    Given a regex/blob of servers, expand to a list
    of server ids.
    """


    # FIXME: we need to refactor expand_servers, it seems to do
    # weird things, reload the config and groups config everytime it's
    # called for one, which may or may not be bad... -akl
    config  = read_config(CONFIG_FILE, CMConfig)

    if noglobs:
        if not just_fqdns:
            return [ "https://%s:%s" % (spec, port) ]
        else:
            return spec

    group_class = groups.Groups()
    group_dict = group_class.get_groups()

    all_hosts = []
    all_certs = []
    seperate_gloobs = spec.split(";")
    new_hosts = []

    # we notate groups with @foo annotation, so look for that in the hostnamegoo
    for each_gloob in seperate_gloobs:
        if each_gloob[0] == '@':
            if group_dict.has_key(each_gloob[1:]):
                new_hosts = new_hosts + group_dict[each_gloob[1:]]
            else:
                print "group %s not defined" % each_gloob

    seperate_gloobs = seperate_gloobs + new_hosts
    for each_gloob in seperate_gloobs:
        actual_gloob = "%s/%s.cert" % (config.certroot, each_gloob)
        certs = glob.glob(actual_gloob)
        for cert in certs:
            all_certs.append(cert)
            host = cert.replace(config.certroot,"")[1:-5]
            all_hosts.append(host)

    all_urls = []
    for x in all_hosts:
        if not just_fqdns:
            all_urls.append("https://%s:%s" % (x, port))
        else:
            all_urls.append(x)

    if verbose and len(all_urls) == 0:
        sys.stderr.write("no hosts matched\n")

    return all_urls


# does the hostnamegoo actually expand to anything?
def isServer(server_string):
    servers = expand_servers(server_string)
    if len(servers) > 0:
        return True
    return False


class Client(object):

    def __init__(self, server_spec, port=DEFAULT_PORT, interactive=False,
        verbose=False, noglobs=False, nforks=1, config=None, async=False, noexceptions=True):
        """
        Constructor.
        @server_spec -- something like "*.example.org" or "foosball"
        @port -- is the port where all funcd processes should be contacted
        @verbose -- whether to print unneccessary things
        @noglobs -- specifies server_spec is not a glob, and run should return single values
        @config -- optional config object
        """
        self.config  = config
        if config is None:
            self.config  = read_config(CONFIG_FILE, CMConfig)
    

        self.server_spec = server_spec
        self.port        = port
        self.verbose     = verbose
        self.interactive = interactive
        self.noglobs     = noglobs
        self.nforks      = nforks
        self.async       = async
        self.noexceptions= noexceptions
        
        self.servers  = expand_servers(self.server_spec, port=self.port, noglobs=self.noglobs,verbose=self.verbose)

        # default cert/ca/key is the same as the certmaster ca - need to
        # be able to change that on the cli
        self.key = '%s/funcmaster.key' % self.config.cadir
        self.cert = '%s/funcmaster.crt' % self.config.cadir
        # yes, they're the same, that's the point
        self.ca = '%s/funcmaster.crt' % self.config.cadir


    def __getattr__(self, name):
        """
        This getattr allows manipulation of the object as if it were
        a XMLRPC handle to a single machine, when in reality it is a handle
        to an unspecified number of machines.

        So, it enables stuff like this:

        Client("*.example.org").yum.install("foo")

        # WARNING: any missing values in Client's source will yield
        # strange errors with this engaged.  Be aware of that.
        """

        return CommandAutomagic(self, [name], self.nforks)

    # -----------------------------------------------

    def job_status(self, jobid):
        """
        Use this to acquire status from jobs when using run with async client handles
        """
        return jobthing.job_status(jobid)

    # -----------------------------------------------

    def run(self, module, method, args, nforks=1):
        """
        Invoke a remote method on one or more servers.
        Run returns a hash, the keys are server names, the values are the
        returns.

        The returns may include exception objects.
        If Client() was constructed with noglobs=True, the return is instead
        just a single value, not a hash.
        """

        results = {}

        def process_server(bucketnumber, buckets, server):
            
            conn = sslclient.FuncServer(server, self.key, self.cert, self.ca )
            # conn = xmlrpclib.ServerProxy(server)

            if self.interactive:
                sys.stderr.write("on %s running %s %s (%s)\n" % (server,
                    module, method, ",".join(args)))

            # FIXME: support userland command subclassing only if a module
            # is present, otherwise run as follows.  -- MPD

            try:
                # thats some pretty code right there aint it? -akl
                # we can't call "call" on s, since thats a rpc, so
                # we call gettatr around it.
                meth = "%s.%s" % (module, method)
                retval = getattr(conn, meth)(*args[:])
                if self.interactive:
                    print retval
            except Exception, e:
                retval = e
                if self.interactive:
                    sys.stderr.write("remote exception on %s: %s\n" %
                        (server, str(e)))
                if self.noglob and not self.noexceptions:
                    raise(e)

            if self.noglobs:
                return retval
            else:
                left = server.rfind("/")+1
                right = server.rfind(":")
                server_name = server[left:right]
                return (server_name, retval)

        if not self.noglobs:
            if self.nforks > 1 or self.async:
                # using forkbomb module to distribute job over multiple threads
                if not self.async:
                    results = forkbomb.batch_run(self.servers, process_server, nforks)
                else:
                    results = jobthing.batch_run(self.servers, process_server, nforks)
            else:
                # no need to go through the fork code, we can do this directly
                results = {}
                for x in self.servers:
                    (nkey,nvalue) = process_server(0, 0, x)
                    results[nkey] = nvalue    
        else:
            # globbing is not being used, but still need to make sure
            # URI is well formed.
            results = process_server(0, 0, self.servers)
            #expanded = expand_servers(self.server_spec, port=self.port, noglobs=True, verbose=self.verbose)[0]
#            results = process_server(0, 0, expanded)

        return results

   # -----------------------------------------------

    def cli_return(self,results):
        """
        As the return code list could return strings and exceptions
        and all sorts of crazy stuff, reduce it down to a simple
        integer return.  It may not be useful but we need one.
        """
        numbers = []
        for x in results.keys():
            # faults are the most important
            if type(x) == Exception:
                return -911
            # then pay attention to numbers
            if type(x) == int:
                numbers.append(x)

        # if there were no numbers, assume 0
        if len(numbers) == 0:
            return 0

        # if there were numbers, return the highest
        # (presumably the worst error code
        max = -9999
        for x in numbers:
            if x > max:
                max = x
        return max
