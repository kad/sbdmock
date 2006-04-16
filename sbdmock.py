#!/usr/bin/python -tt
# vim: sw=4 ts=4 expandtab ai 
#
# This file is part of sbdmock
#
# Copyright (C) 2005,2006 Alexandr Kanevskiy
#
# Contact: Alexandr D. Kanevskiy <packages@bifh.org>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA
# 02110-1301 USA
#
# $Id$

import os
import os.path
import sys
import commands
import glob
import shutil
import types
import grp
import tempfile
import re
import urllib
import time
import popen2
from exceptions import Exception
from optparse import OptionParser

# local modules
# debug
# sys.path.append("./")
from minideblib.ChangeFile import ChangeFile

__VERSION__ = "r"+"$Revision$"[11:-2]

# Fixed settings, do not change these unless you really know what you are doing
PackageRegex = "[a-z0-9][a-z0-9.+-]+"        # Regular expression package names must comply with
VersionRegex = "(?:[0-9]+:)?[a-zA-Z0-9.+-]+" # Regular expression package versions must comply wi


def error(msg):
    """Prints error to stderr"""
    print >> sys.stderr, msg

def strtimestamp():
    """Return string with timestamp"""
    timestamp = time.strftime("[%F %T]")
    return timestamp

class Error(Exception):
    """ Base error class """
    def __init__(self, msg):
        Exception.__init__(self)
        self.msg = msg
        self.resultcode = 1

class BuildError(Error):
    """ Error generated in case of build problems """
    def __init__(self, msg):
        Error.__init__(self, msg)
        self.msg = msg
        self.resultcode = 10

class RootError(Error):
    """ Error generated in case of problems while setting-up environment """
    def __init__(self, msg):
        Error.__init__(self, msg)
        self.msg = msg
        self.resultcode = 20

class AptError(Error):
    """ Error generated in case of problems with apt """
    def __init__(self, msg):
        Error.__init__(self, msg)
        self.msg = msg
        self.resultcode = 30

class PkgError(Error):
    """ Error generated in case of problems with package itself """
    def __init__(self, msg):
        Error.__init__(self, msg)
        self.msg = msg
        self.resultcode = 40

class SBError(Error):
    """ Error generated in case of problems with Scratchbox """
    def __init__(self, msg):
        Error.__init__(self, msg)
        self.msg = msg
        self.resultcode = 50


class SBBuilder:
    """base Scratcbox builder object"""
    def __init__(self, config):
        self._state = 'unstarted'
        self.tmplog = []
        self.config = config

        self.sbbasedir = config['basedir']
        self.sb_homedir = config['sb_homedir']
        self.basedir = self.sbbasedir+self.sb_homedir
        
        root = config['root']
        self.sbtarget = config['sbtarget']

        self.sbtargetdir = os.path.join(self.sbbasedir, 'targets', self.sbtarget)

        self.builddir = os.path.join(self.basedir, root)
        

        self.sb_builddir = os.path.join(self.sb_homedir, root)
        self.sb_resultdir = os.path.join(self.sb_builddir, "result")
        
        self.workdir = os.path.join(self.builddir, "work")
        self.sb_workdir = os.path.join(self.sb_builddir, "work")

        if not self.config.has_key('resultdir'):
            self.resultdir = os.path.join(self.builddir, 'result')
        else:
            self.resultdir = self.config['resultdir']
        if not self.config.has_key('statedir'):
            self.statedir = os.path.join(self.builddir, 'state')
        else:
            self.statedir = self.config['statedir']

        self._ensure_dir(self.statedir)
        self.state("init")

        if config['clean']:
            self.clean()

        self._ensure_dir(self.builddir)
        self._ensure_dir(self.workdir)
        self._ensure_dir(self.statedir)
        self._ensure_dir(self.resultdir)

        # open the log files
        root_log = os.path.join(self.resultdir, 'root.log')
        self._root_log = open(root_log, 'w+')
        build_log = os.path.join(self.resultdir, 'build.log')
        self._build_log = open(build_log, 'w+')

        # write out the config file
        cfg_log = os.path.join(self.resultdir, 'sbdmockconfig.log')
        cfgout = open(cfg_log, 'w+')
        cfgout.write('builddir=%s\n' % self.builddir)
        cfgout.write('resultdir=%s\n' % self.resultdir)
        cfgout.write('statedir=%s\n' % self.statedir)
        cfgout.flush()
        cfgout.close()



    def build_log(self, content):
        """Write content (it could be string or array of strings) to build.log"""
        if type(content) is types.ListType:
            for line in content:
                self._build_log.write('%s\n' % line)
        elif type(content) is types.StringType:
            self._build_log.write('%s\n' % content)
        else:
            # wtf?
            pass
        self._build_log.flush()

    def root_log(self, content):
        """Write content (it could be string or array of strings) to root.log"""
        # do this so if the log dir isn't ready yet we can still get those logs
        self.tmplog.append(content)

        if not hasattr(self, '_root_log'):
            return

        for content in self.tmplog:
            if type(content) is types.ListType:
                self._root_log.write('%s\n' % strtimestamp())
                for line in content:
                    self._root_log.write('%s\n' % line)
            elif type(content) is types.StringType:
                self._root_log.write('%s %s\n' % (strtimestamp(), content))
            else:
                # wtf?
                pass

            self._root_log.flush()
        self.tmplog = [] # zero out the logs

    def debug(self, msg):
        """ Print debug messages on stdout, if debug option enabled """
        if self.config['debug']:
            print "%s DEBUG: %s" % (strtimestamp(), msg)

    def state(self, curstate=None):
        """returns/writes state. If curstate is given then write the
           state out and report it back. If curstate is not given report
           self.state"""

        if curstate:
            statusfile = os.path.join(self.statedir, 'status')
            sfo = open(statusfile, 'w')
            sfo.write('%s\n' % curstate)
            sfo.close()
            self._state = curstate
            print "%s %s" % (strtimestamp(), curstate)
        else:
            return self._state

    def clean(self):
        """clean out chroot with extreme prejudice :)"""
        self.state("clean")

        self.root_log('Cleaning Root')

        self._sb_reset_target()
        # cleanup workdir
        if os.path.exists(self.builddir):
            cmd = '%s -rfv %s' % (self.config['rm'], self.builddir)
            (retval, output) = self.do(cmd)

            if retval != 0:
                error("Errors cleaning out chroot: %s" % output)
                if os.path.exists(self.builddir):
                    raise RootError, "Failed to clean basedir, exiting"
        # We need to cleanup host_usr hacks after usage of it
        host_usr_dict = self.config['host_usr']
        for key in host_usr_dict:
            fname = '%s/host_usr/bin/%s' % (self.sbbasedir, key)
            self.debug("Removing host_usr hack file %s" % fname)
            try:
                os.unlink(fname)
            except:
                # we can ignore error here, if file not present
                pass
 

    def prep(self):
        """prepare root"""
        self.state("prep")

        self._prep_install()
        # Extract rootstrap only if it's defined
        if self.config['rootstrap']:
            self._sb_extract_rootstrap()
        else:
            # Copy Toolchain C library only, if we don't have rootstrap
            self._sb_copy_libc()
        # But always copy correct fakeroot library
        self._sb_copy_fakeroot()
        # After each rootstrap extraction, we need to replace special files in target
        self._sb_extract_special_files()
        self.apt("update")


    def apt(self, cmd):
        """executes apt-get inside target"""
        basecmd = "fakeroot apt-get -y -q "
        command = '%s %s </dev/null' % (basecmd, cmd)
        self.debug("apt: command %s" % command)

        self.root_log(command)
        (retval, output) = self.do_chroot_ng(command)
        #self.root_log(output)

        if retval != 0:
            raise AptError, "Error peforming apt-get command: %s" % command

        return (retval, output)
    
    def build(self, dsc):
        """build an source package into binary debs, capture log"""

        self.state("setup")

        orgdir = os.path.dirname(dsc)
        dscname = os.path.basename(dsc)
        cdsc = ChangeFile()
        cdsc.load_from_file(dsc)
        try:
            cdsc.verify(orgdir)
        except Exception, err:
            raise PkgError, "Source package verification failed: %s" % err

        self.root_log("Copying source files to work dir")

        filelist = []
        filelist.append(dscname)
        for item in cdsc.getFiles():
            filelist.append(item[4]) 
        for file in filelist:
            self.debug("copying file %s" % file)
            shutil.copy2(os.path.join(orgdir, file), self.workdir)

        self.root_log("Extracting sources to work dir")
        cmd = "cd %s && dpkg-source -x %s " % (self.sb_workdir, dscname)
        self.root_log(cmd)
        (retval, output) = self.do_chroot(cmd)
        self.root_log(output)
        
        match = re.search('dpkg-source: extracting .+ in (.+)(?:\s.+)?$', output)
        if match:
            pkgsubdir = match.group(1)
        else:
            self.debug("dpkg-source output: %s" % output)
            raise PkgError, "Can't parse output of dpkg-source"

        self.install_build_deps(pkgsubdir)
    
        # take source package, pass to install_build_deps() and do build 
        cmd = "cd %s && %s" % (os.path.join(self.sb_workdir, pkgsubdir), self.config['dpkg-buildpackage'])
        self.state("build")

        #self.root_log(cmd)
        (retval, output) = self.do_chroot_ng(cmd)

        #self.build_log(output)

        if retval != 0:
            raise BuildError, "Error building package %s, See build log" % dsc

        changes = glob.glob(os.path.join(self.workdir,"*.changes"))
        changes_file = changes[0]

        chgs = ChangeFile()
        chgs.load_from_file(changes_file)
        try:
            chgs.verify(self.workdir)
        except Exception, err:
            raise BuildError, "Built packages verification failed: %s" % err

        filelist = []
        filelist.append(changes_file)
        for item in chgs.getFiles():
            filelist.append(item[4]) 

        self.root_log("Copying packages to result dir")
        for item in filelist:
            shutil.copy2(os.path.join(self.workdir, item), self.resultdir)



    def install_build_deps(self, pkgsubdir):
        """try to satisfy build-deps for package"""

        self.debug("Checking build-deps first time")
        builddeps = self._sb_check_pkg_builddepends(pkgsubdir)
        if not builddeps:
            self.debug("We are lucky, all deps already here")
            return

        self.root_log("Trying to install build-deps")
        (ret, builddeps) = self._sb_try_satisfy_build_deps(builddeps, pkgsubdir)
        if ret and not builddeps:
            return

        # For safety, let's try one more time
        #self.root_log("Ensure build-deps")
        #(ret, builddeps) = self._sb_try_satisfy_build_deps(builddeps, pkgsubdir)
        #if ret and not builddeps:
        #    return
       
        self.root_log("Checking build environment...")
        builddeps = self._sb_check_pkg_builddepends(pkgsubdir)
        if builddeps:
            self.root_log("Unable to satisfy build-deps: %s" % builddeps)
            raise PkgError, "Unable to satisfy build-deps: %s" % builddeps
        self.root_log("Seems ok")


    def _sb_try_satisfy_build_deps(self, builddeps, pkgsubdir):
        """ Tries to satisfy build dependencies by apt-get & dpkg-checkbuilddeps"""
        self.debug("Builddeps: '%s'" % builddeps)
        depends, variants = self._deb_build_alts(builddeps)
        if depends:
            self.root_log("Try to install static depends: %s" % depends)
            self.apt("install --no-remove %s" % depends)
        bdep = ""
        if variants:
            for variant in variants:
                self.root_log("Try to install alt dependencies: %s" % variant)
                try:
                    self.apt("install --no-remove %s" % variant)
                except AptError:
                    # we can skip that error, and try another variant
                    continue
                self.root_log("Checking dependencies...")
                bdep = self._sb_check_pkg_builddepends(pkgsubdir)
                if not bdep:
                    self.root_log("Build-deps satisfied")
                    return (True,'')
                else:
                    self.root_log("Unmet build-dep: %s Trying next variant" % bdep)
        if not bdep:
            bdep =  self._sb_check_pkg_builddepends(pkgsubdir)
            if not bdep: 
                return (True, '')
            else:
                return (False, bdep)
        else:
            self.root_log("Some dependencies still unmet: %s" % bdep)
            return (False, bdep)

    def _sb_check_pkg_builddepends(self, pkgsubdir):
        """Executes dpkg-checkbuilddeps and provides result"""
        self.debug("Checking dependencies ...")
        cmd = "cd %s && dpkg-checkbuilddeps" % os.path.join(self.sb_workdir, pkgsubdir)
        self.root_log(cmd)
        (retval, output) = self.do_chroot(cmd)
        
        if retval == 0:
            self.debug("All dependencies already met")
            return None
        m = re.search('dpkg-checkbuilddeps: Unmet build dependencies: (.+)$', output)
        if m:
            builddeps = m.group(1)
        else:
            self.debug("dpkg-checkbuilddeps output: %s" % output)
            raise PkgError, "Can't parse output of dpkg-checkbuilddeps"
        self.debug("Unment build dependencies: %s" % builddeps)
        return builddeps.strip()


    def _deb_build_alts(self, builddeps):
        """make array of variants in case"""
        variants = []
        # let's strip version deps, apt-get dosn't understand it
        builddeps = re.sub('\(.+?\)', "", builddeps)
        # Do we have alts ?
        if builddeps.find('|') < 0:
            # we are lucky, only one variant
            #variants.append(builddeps)
            #return variants
            return (builddeps, [])
        else:
            regexp = "("+PackageRegex + "(\s*\|\s*" + PackageRegex +")+)"
            alts_arr = []
            alts = re.findall(regexp, builddeps)
            for s in alts:
                if len(s) == 2:
                    # array of matches
                    builddeps = builddeps.replace(s[0], "")
                    alts_arr.append(re.split('\s*\|\s*', s[0]))
                else:
                    # match itself?
                    builddeps = builddeps.replace(s, "")
                    alts_arr.append(re.split('\s*\|\s*', s))
            v = self._mss_variants(alts_arr)
            for item in v:
                s = " ".join(item)
                variants.append(s)
            return (builddeps, variants)


    def _mss_variants(self, deps):
        variants = [[]]

        for dep in deps:
            if len(dep) == 1:
                for i in range(len(variants)):
                    variants[i].append(dep)
            else:
                nvariants = []
                for candidate in dep:
                    for variant in variants:
                        nvariants.append(variant + [candidate, ])
                variants = nvariants
        return variants    


    def close(self):
        """unmount things and clean up a bit"""
        self.root_log("Cleaning up...")
        self.state("ending")
        self._build_log.close()
        self.state("done")
        self.root_log("Done.")
        self._root_log.close()


    def _ensure_dir(self, path):
        """check for dir existence and/or makedir, if error out then raise Error"""

        msg = "ensuring dir %s" % path
        self.debug(msg)
        self.root_log("%s" % msg)

        if not os.path.exists(path):
            try:
                os.makedirs(path)
            except OSError, err:
                raise Error, "Could not create dir %s. Error: %s" % (path, err)


    def _sb_reset_target(self):
        """cleanup target and put required libraries in place"""
        self._ensure_dir(self.builddir)
        # Try to unmount NFS, if current target use sbrsh
        self.do_chroot('if [ "x$SBOX_CPUTRANSPARENCY_METHOD" == "xsbrsh" ]; then sbrsh $SBOX_TARGET_NAME --umount-all ; fi')
        # insure active target
        self.do_chroot("sbox-config -st %s" % self.sbtarget)
        if not self._sb_ensure_target(self.sbtarget):
            raise SBError, "Failed to select target %s, exiting" % self.sbtarget

        # If no key in config, try to unmount, to be safe
        if not self.config.has_key('sbrsh') or self.config['sbrsh']:
            # Try to unmount NFS before reset
            self.do_chroot('if [ "x$SBOX_CPUTRANSPARENCY_METHOD" == "xsbrsh" ]; then sbrsh $SBOX_TARGET_NAME --umount-all ; fi')
        # cleanup target
        self.do_chroot("sbox-config -rt")

    def _sb_copy_fakeroot(self):
        """Copy fakeroot library to the target"""
        self.do_chroot("sbox-config -cf")


    def _sb_copy_libc(self):
        """Copy C library to the target"""
        self.do_chroot("sbox-config -cc")


    def _sb_make_cmdfile(self, command, fd):
        """make cmd file for execution inside scratchbox"""
        os.write(fd,'#!/bin/bash\n\n') 
        os.write(fd,'# !!! Automatic temporary file. Do not touch !!!\n') 
        os.write(fd,'\n\necho "SBDMOCK-AUTO: Setup Environment"\n') 
        os.write(fd,'source /targets/links/scratchbox.config\n\n') 
        os.write(fd,'# Configuration environment options: \n')
        for variable, value in self.config['env'].iteritems():
            os.write(fd,'export %s="%s"\n' % (variable, value))
        if self.config['host_usr']:
            os.write(fd,'export PATH=/host_usr/bin:$PATH\n')
            # MSS: is it not a bit too demanding for the shell? how many items we usually have in host_usr?
            # KAD: multiple lines is much easier to debug, in case something goes wrong
            host_usr_dict = self.config['host_usr']
            for key in host_usr_dict:
                os.write(fd, 'export SBOX_REDIRECT_BINARIES=$SBOX_REDIRECT_BINARIES,/usr/bin/%s:/host_usr/bin/%s\n' % (key, key))
        os.write(fd, '\n\necho "SBDMOCK-AUTO: Start"\n') 
        os.write(fd, command+"\n")
        os.write(fd, '\n\necho "SBDMOCK-AUTO: Status = $?"\n') 

    def _sb_parse_output(self, cmdoutput):
        """parses cmdoutput and return real status value of command"""
        
        match = re.search("^SBDMOCK-AUTO: Setup Environment$\n^(.*)$\n+^SBDMOCK-AUTO: Status = ([0-9-]+)", cmdoutput, re.M+re.S)
        if not match:
            self.debug("Unable to parse cmdoutput: %s " % cmdoutput)
            #return (None, cmdoutput)
            #FIXME: what to return in case of parse error ?
            return (200, cmdoutput)
        output = match.group(1)
        output = re.sub("SBDMOCK-AUTO:.+", "", output)
        try:
            retval = int(match.group(2))
        except:
            retval = 210
            self.debug("Error converting parsed result to integer: %s" % match.group(2))
        return (retval, output)

    def _sb_ensure_target(self, entarget):
        """checks current active target"""
        #self.debug("_sb_ensure_target %s" % entarget)
        (retval, output) = self.do_chroot('echo "SBOX_TARGET_NAME=$SBOX_TARGET_NAME"')
        self.debug("Return code: %d" % retval)
        match = re.search("\n*SBOX_TARGET_NAME=(.+)\n*", output, re.M)
        if not match:
            self.debug("Can't find target in output: %s" % output)
            return False
        #self.debug("SB Target %s" % m.group(1))
        if match.group(1) != entarget:
            return False
        else:
            return True

    def _sb_extract_rootstrap(self):
        """get (if not local) rootstrap, and extract to target"""
        rootstrap = self.config['rootstrap'] 

        if rootstrap.find('http://') == 0:
            self.debug("_sb_extract_rootstrap: remote rootstrap. needs to be fetched")
            opener = urllib.URLopener()
            try:
                #self.debug(os.path.join(self.builddir,"rootstrap.tgz"))
                #self.debug(rootstrap)
                self.root_log("Retreiving remote rootstrap: %s" % rootstrap)
                opener.retrieve(rootstrap, os.path.join(self.builddir, "rootstrap.tgz"))
            except IOError, err:
                self.root_log("Failed to fetch %s: %s" % (rootstrap, str(err)))
                raise RootError, "Failed to fetch %s: %s" % (rootstrap, str(err))
            rootstrap = os.path.join(self.sb_builddir, "rootstrap.tgz")

        self.root_log("Extracting rootstrap %s" % rootstrap)
        # Local sbox file, just run it
        (status, output) = self.do_chroot("sbox-config -er %s" % rootstrap)
        if output.find("_SBOX_RESTART_FILE") >= 0:
            # Workarround
            status = 0
        if status != 0:
            self.debug("Error output: "+output)
            raise SBError, "Failed to extract rootstrap, exiting"
        self.root_log(output)

    def do_sbox(self, command):
        """execute given command via scratchbox"""

        self.debug("Executing(scratchbox) %s" % command)
        (sbtmpfd, sbtmpname) = tempfile.mkstemp('.sh', 'sbdmock-', self.builddir)
        sb_tmpname = sbtmpname[len(self.sbbasedir):]
        #self.debug("tmpfile %s %s" % (sbtmpname,sb_tmpname))
        
        self._sb_make_cmdfile(command, sbtmpfd) 
        os.close(sbtmpfd)
        os.chmod(sbtmpname, 0700)

        (status, output) = commands.getstatusoutput( "%s %s" % (self.config['scratchbox'], sb_tmpname))
        self.debug("Return status: %d" % status)

        (retval, output) = self._sb_parse_output(output)
        os.unlink(sbtmpname)
        
        return (retval, output)

    def do_sbox_ng(self, command):
        """ The same as do_sbox, but make logs tailable"""

        self.debug("Executing(scratchbox) %s" % command)
        (sbtmpfd, sbtmpname) = tempfile.mkstemp('.sh', 'sbdmock-', self.builddir)
        sb_tmpname = sbtmpname[len(self.sbbasedir):]
        #self.debug("tmpfile %s %s" % (sbtmpname,sb_tmpname))
        
        self._sb_make_cmdfile(command, sbtmpfd) 
        os.close(sbtmpfd)
        os.chmod(sbtmpname, 0700)

        pipe = popen2.Popen4("%s %s </dev/null" % (self.config['scratchbox'], sb_tmpname))
        # We will only read from pipe
        pipe.tochild.close()
       
        logfile = self._root_log
        if self.state() == "build":
            logfile = self._build_log
        output = ""
        collect = False
        retval = None
        if self.config['debug']:
            collect = True
        
        #for line in pipe.fromchild:
        while True:
            line = pipe.fromchild.readline()
            if not line:
                break
            if not collect and line.startswith("SBDMOCK-AUTO: Start"):
                collect = True
                continue
            if collect and line.startswith("SBDMOCK-AUTO: Status = "):
                if not self.config['debug']:
                    collect = False
                retval = int(line[len("SBDMOCK-AUTO: Status = "):])
                continue
            if collect:
                logfile.write(line)
                logfile.flush()
                self.debug(line)
                output += line

        pipe.fromchild.close()
        status = pipe.wait()
        self.debug("SB return code: %d" % status)

        os.unlink(sbtmpname)
        if retval == None:
            # Something strange happend. Got killed ?
            retval = -1
        
        return (retval, output)


    def do(self, command):
        """execute given command outside of chroot"""

        self.debug("Executing %s" % command)
        (status, output) = commands.getstatusoutput(command)

        if os.WIFEXITED(status):
            retval = os.WEXITSTATUS(status)

        return (retval, output)

    def do_chroot(self, command, fatal = False, exitcode=None):
        """execute given command in sbox target"""

        (ret, output) = self.do_sbox(command)
        if (ret != 0) and fatal:
            self.close()
            if exitcode:
                ret = exitcode

            error("Non-zero return value %d on executing %s\n" % (ret, command))
            sys.exit(ret)

        return (ret, output)

    def do_chroot_ng(self, command, fatal = False, exitcode=None):
        """execute given command in sbox target"""

        (ret, output) = self.do_sbox_ng(command)
        if (ret != 0) and fatal:
            self.close()
            if exitcode:
                ret = exitcode

            error("Non-zero return value %d on executing %s\n" % (ret, command))
            sys.exit(ret)

        return (ret, output)

    def _prep_install(self):
        """prep sb target for installation"""
        # switch to target
        # reset target
        # copy fakeroot libraries

        # If "clean" set, we already have clean target
        if not self.config['clean']:
            self._sb_reset_target()
            # KAD: do we need it here ? 
            self._sb_copy_fakeroot()

    def _sb_extract_special_files(self):
        # write in sources.list into chroot
        aptsconf = os.path.join(self.sbtargetdir, 'etc', 'apt','sources.list')
        self.debug("Extracting sources.list (%s)" % aptsconf)
        aptsconf_fo = open(aptsconf, 'w')
        aptsconf_content = self.config['sources.list']
        aptsconf_fo.write(aptsconf_content)

        # files in /etc that need doing
        filedict = self.config['files']
        for key in filedict:
            fn = '%s%s' % (self.sbtargetdir, key)
            self.debug("Extracting file %s" % fn)
            fo = open(fn, 'w')
            fo.write(filedict[key])
            fo.close()
        host_usr_dict = self.config['host_usr']
        for key in host_usr_dict:
            fn = '%s/host_usr/bin/%s' % (self.sbbasedir, key)
            self.debug("Extracting host_usr hack file %s" % fn)
            fo = open(fn, 'w')
            fo.write(host_usr_dict[key])
            fo.close()
            # Make it executable
            os.chmod(fn, 0755)
 

def command_parse():
    """return options and args from parsing the command line"""

    usage = """
    usage: sbdmock [options] /path/to/dsc
    optional commands:
        clean - clean out the specified chroot
        init - initialize the chroot, do not build anything"""
    parser = OptionParser(usage=usage, version=__VERSION__)
    parser.add_option("-r", action="store", type="string", dest="target",
                      default='default',
                      help="compilation target name/config file name default: %default")
    parser.add_option("--no-clean", action ="store_true", dest="dirty",
             help="do not clean chroot before building")
    parser.add_option("--debug", action ="store_true", dest="debug",
             default=False, help="Output copious debugging information")
    parser.add_option("--resultdir", action="store", type="string",
             default=None, help="path for resulting files to be put")
    parser.add_option("--statedir", action="store", type="string", default=None,
            help="path for state dirresulting files to be put")
    parser.add_option("--sbtarget", action="store", type="string", default=None,
            help="Overrides scratchbox target name from configuration file")
    parser.add_option("--addrepo", action="append", type="string", default=None,
            help="Additional repository to sources.list")
    parser.add_option("--insertrepo", action="append", type="string", default=None,
            help="Additional repository to sources.list. Will be added on first place")
    #parser.add_option("--uniqueext", action="store", type="string", default=None,
    #        help="Arbitrary, unique extension to append to buildroot directory name")

    return parser.parse_args()

def main():
    """ Debian package builder for Scratchbox environment """
    member = False
    for item in os.getgroups():
        try:
            grptup = grp.getgrgid(item)
        except KeyError:
            continue
        
        if grptup[0] == 'sbox':
            member = True

    if not member:
        print "You need to be a member of the sbox group for use scratchbox"
        sys.exit(1)

    # and make sure they're not root
    if os.geteuid() == 0:
        error("Don't try to run this programm as root!")
        sys.exit(1)

    # config path
    config_path = '/etc/sbdmock'
    config_path_user = os.path.join(os.environ['HOME'], '.sbdmock')

    # defaults
    config_opts = {}
    config_opts['clean'] = True
    config_opts['debug'] = False
    config_opts['basedir'] = os.path.join('/scratchbox/users', os.environ['USER'])
    config_opts['sb_homedir'] = os.path.join('/home', os.environ['USER'])
    config_opts['files'] = {}
    config_opts['files'] = {}
    config_opts['host_usr'] = {}
    config_opts['env'] = {}
    config_opts['rm'] = 'rm'
    config_opts['dpkg-buildpackage'] = 'dpkg-buildpackage -rfakeroot -uc -us -sa -D'
    config_opts['scratchbox'] = '/usr/bin/scratchbox'
    config_opts['sources.list'] = ''
    #config_opts['files']['/etc/resolv.conf'] = "nameserver 192.168.1.1\n"
    #config_opts['files']['/etc/hosts'] = "127.0.0.1 localhost localhost.localdomain\n"

    # cli option parsing
    (options, args) = command_parse()

    if len(args) < 1:
        error("No dsc or command specified - nothing to do")
        sys.exit(50)

    # read in the config file by chroot name
    if options.target.endswith('.cfg'):
        cfg = '%s/%s' % (config_path, options.target)
        ucfg = '%s/%s' % (config_path_user, options.target)
    else:
        cfg = '%s/%s.cfg' % (config_path, options.target)
        ucfg = '%s/%s.cfg' % (config_path_user, options.target)

    configured = False

    # Try to load global configuration file
    if os.path.exists(cfg):
        execfile(cfg)
        configured = True
    # Try to merge local user settings, if any...
    if os.path.exists(ucfg):
        execfile(ucfg)    
        configured = True
        
    # Are we ready ?
    if not configured:
        error("Could not find config file (%s or %s) for target %s" % (cfg, ucfg, options.target))
        sys.exit(1)

    if not config_opts.has_key('root'):
        if options.target.endswith('.cfg'):
            config_opts['root'] = options.target[:-4]
        else:
            config_opts['root'] = options.target

    configured = None

    if options.dirty:
        config_opts['clean'] = False

    if options.debug: 
        config_opts['debug'] = True

    if options.resultdir:
        config_opts['resultdir'] = options.resultdir

    if options.statedir:
        config_opts['statedir'] = options.statedir

    if options.sbtarget:
        config_opts['sbtarget'] = options.sbtarget

    if options.addrepo:
        # Append to sources lists repositories from command line
        config_opts['sources.list'] +="\n# Repositories added from command line\n" 
        for repo in options.addrepo:
            config_opts['sources.list'] += repo+"\n"

    if options.insertrepo:
        # Insert on first places to sources lists repositories from command line
        insert_repos = "# Repositories inserted from command line\n" 
        for repo in options.insertrepo:
            insert_repos += repo+"\n"
        config_opts['sources.list'] = insert_repos + "\n# Repositories from config file\n" + config_opts['sources.list']

    # do whatever we're here to do
    if args[0] == 'clean':
        # unset a --no-clean
        config_opts['clean'] = True
        try:
            my = None
            my = SBBuilder(config_opts)
        except Error, err:
            error("Error occured: %s" % err.msg)
            if my:
                my.close()
            sys.exit(err.resultcode)

        my.close()
        print 'Finished cleaning target'

    elif args[0] == 'init':
        try:
            my = None
            my = SBBuilder(config_opts)
            my.prep()
        except Error, err:
            error("Error occured: %s" % err.msg)
            if my:
                my.close()
            sys.exit(err.resultcode)

        my.close()
        print 'Finished initializing target'

    else:
        if args[0] == 'rebuild':
            if len(args) > 1:
                dsc = args[1]
            else:
                error("No package specified to rebuild command.")
                sys.exit(50)
        else:
            dsc = args[0]

        if not os.path.exists(dsc):
            error("Unable to find source package '%s'." % dsc)
            sys.exit(50)

        start_time = time.time()
        try:
            my = None  
            my = SBBuilder(config_opts)
            my.prep()
            my.build(dsc)
        except Error, err:
            error("Error occured: %s" % err.msg)
            if my:
                my.close()
            sys.exit(err.resultcode)

        my.close()
        stop_time = time.time()
        print "Elapsed time %s" % time.strftime("%T", time.gmtime(stop_time-start_time))
        print "Results and/or logs in: %s" % my.resultdir


if __name__ == '__main__':
    main()
