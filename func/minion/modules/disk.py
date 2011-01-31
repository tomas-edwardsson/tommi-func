#
# Copyright 2009
# Greg Swift <gregswift@gmail.com>
#
# This software may be freely redistributed under the terms of the GNU
# general public license.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

import func_module
from func.minion import sub_process

class DiskModule(func_module.FuncModule):
    version = "0.0.1"
    api_version = "0.0.1"
    description = "Gathering disk related information"

    def usage(self, partition=None):
        """
        Returns the results of df -PT
        """
        results = {}
        # splitting the command variable out into a list does not seem to function
        # in the tests I have run
        command = '/bin/df -PT'
        if (partition):
            command += ' %s' % (partition)
        cmdref = sub_process.Popen(command, stdout=sub_process.PIPE,
                                   stderr=sub_process.PIPE, shell=True,
                                   close_fds=True)
        (stdout, stderr) = cmdref.communicate()
        for disk in stdout.split('\n'):
            if (disk.startswith('Filesystem') or not disk):
                continue
            (device, fstype, total, used, available, percentage, mount) = disk.split()
            results[mount] = {'device':device,
                              'total':str(total),
                              'used':str(used),
                              'available':str(available),
                              'fstype':str(fstype),
                              'percentage':int(percentage[:-1])}
        return results

    def register_method_args(self):
        """
        The argument export method
        """
        return {
                'usage':{
                    'args':{
                        'partition': {
                            'type':'string',
                            'optional':True,
                            'description':'A specific partition to get usage data for',
                            }
                        },
                    'description':'Gather disk usage information'
                    }
                }
