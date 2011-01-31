#
# Copyright 2010
# Tomas Edwardsson <tommi@tommi.org>
#
# This software may be freely redistributed under the terms of the GNU
# general public license.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

import func_module
from func.minion import sub_process

class CpuModule(func_module.FuncModule):
    version = "0.0.1"
    api_version = "0.0.1"
    description = "Gathering CPU related information"

    def usage(self):
        """
        Returns the results of vmstat regarding to cpu
        """
        results = {}
        # splitting the command variable out into a list does not seem to function
        # in the tests I have run
        command = 'vmstat 1 2'
        cmdref = sub_process.Popen(command, stdout=sub_process.PIPE,
                                   stderr=sub_process.PIPE, shell=True,
                                   close_fds=True)
        (stdout, stderr) = cmdref.communicate()

        vmstat = stdout.split('\n')[3]

        (user, system, idle, iowait, steal) = vmstat.split()[-5:]
        results = {'user':user, 'system':system, 'idle':idle, 'iowait':iowait, 'steal':steal}
        #for disk in stdout.split('\n'):
            #if (disk.startswith('Filesystem') or not disk):
                #continue
            #(device, total, used, available, percentage, mount) = disk.split()
            #results[mount] = {'device':device,
                              #'total':str(total),
                              #'used':str(used),
                              #'available':str(available),
                              #'percentage':int(percentage[:-1])}
        return results

    def register_method_args(self):
        """
        Implementing the method arg getter
        """

        return{
                'usage':{'args':{},
                    'description':"Listing the cpu usage" }}
