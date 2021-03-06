#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Name: unball unit test script
Copyright 2006, 2009 Stephan Sokolow

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

@todo: Create a pseudo-quine to test recursion limits.
@todo: Add tests for non-StuffIt MacBinary files.
@todo: Add password-protected archive tests to ensure subprocesses don't pause
       to ask for a password.
@todo: Add a BlakHole test archive and figure out a way to reliably identify
       extractors that aren't getting tested, not just extensions.
@todo: Rename this to meet the naming conventions for distutils.
@todo: Add support for returning "skipped" for NoExtractorError.
@todo: Add a test to ensure that tryExtract doesn't start adding extra layers
of containing folders. (especially with stuff like .tar.7z)
@todo: Subclass unittest.TextTestRunner to implement curses-colorized output.
@todo: Re-implement unball verbosity.
@todo: Add a command-line option for testing the old unball binary.
(So that my new tests can be used on the old 0.2.x branch)
@todo: Add support for testing more than just args[0].
@todo: Rework the tests so the test can also validate the resultant directory
tree. (Both structure and file content)
@todo: Improve the tests so they confirm bit-exact output with tiny PNGs to
catch problems like "PipeExtractor used ASCII-mode file handles on Windows."
"""

__author__ = "Stephan Sokolow (deitarion)"
__license__ = "GNU GPL 2.0 or later"

import os, shutil, sys, tempfile

from os import listdir
from os.path import abspath, dirname, normcase, realpath
from optparse import OptionParser

if sys.version_info[0] == 2 and sys.version_info[1] < 7:  # pragma: no cover
    import unittest2 as unittest
    unittest  # Silence erroneous PyFlakes warning
else:                                                     # pragma: no cover
    import unittest

sys.path.append(abspath('./src'))

from unball.extractors import (
        NoExtractorError, UnsupportedFiletypeError,
        EXTRACTORS, FALLBACK_DESCRIPTIONS
)
from unball.main import self_test, tryExtract
from unball.mimetypes import EXTENSIONS

# Files which may be added to the test sources dir without being test sources.
excluded = ['.DS_Store']

# Maps return codes to their meanings.
retcodes = {
            0: 'Extracted OK',
            1: 'A bug trap was triggered',
            2: 'Could not make temp dir',
            3: 'Could not change directories',
            4: 'Could not find requested unarchiving tool',
            5: 'Archive tool returned an error',
            6: 'Could not move files to target dir',
            7: 'Could not delete temporary files/dirs',
            32512: 'Unknown. Could not find a required command in PATH?'
}

# TODO: Why did I do this again?
count_omit = ['jartest.j', 'jartest.jar', 'eartest.ear', 'wartest.war']

# Test files in formats which cannot contain multiple files.
compress_only = [
    'b64test.png.b64',
    'b64test.png.mim',
    'binhextest.bh',
    'binhextest.bhx',
    'binhextest.hqx',
    'bziptest.bz2',
    'bziptest.header',
    'compress_test.txt.Z',
    'compress_test.txt.header',
    'gziptest.gz',
    'gziptest.header',
    'mscompress.tx_',
    'rziptest.rz',
    'uutest.png.uu',
    'uutest.png.uue',
    'xxtest.png.xx',
    'xxtest.png.xxe',
    'yenctest.png.ync',
    'yenctest.png.yenc']

def makeTests(path, verbosity=0):
    """
    Dynamically generate a set of unball unit tests for a given file.
    Used to allow per-format testing of unball in a simple manner.
    """
    filename = os.path.split(path)[1]

    class UnballTestSet(unittest.TestCase):
        """Test unball with a specific archive"""
        def setUp(self):
            """Prepare a temporary test tree in the filesystem."""
            self.workdir = os.path.realpath(tempfile.mkdtemp('-unballtest'))
            # All dirs have spaces in them in order to ensure there are no
            #  space-related bugs remaining.
            self.cwd_dir = os.path.join(self.workdir, 'cwd dir')
            self.srcdir  = os.path.join(self.workdir, 'src dir')
            self.srcfile = os.path.join(self.srcdir, filename)
            self.destdir = os.path.join(self.workdir, 'dest dir')

            os.makedirs(self.srcdir)
            os.makedirs(self.destdir)
            os.makedirs(self.cwd_dir)
            shutil.copyfile(path, self.srcfile)

            self.oldcwd = os.getcwdu()

        def tearDown(self):
            """Make sure the test tree gets deleted."""
            os.chdir(self.oldcwd)
            shutil.rmtree(self.workdir)

    def makeTestMethod(destName, destDir, workDir, realDest):
        """Closure which allows one definition to service all three cases
        for destination directory specification."""
        def testMethod(self, dest=destDir, cwd=workDir, realDest=realDest):
            if dest:
                dest = normcase(realpath(getattr(self, dest)))
            cwd      = normcase(realpath(getattr(self, cwd)))
            realDest = normcase(realpath(getattr(self, realDest)))

            oldcwd = os.getcwd()
            os.chdir(cwd)
            try:
                old_src  = listdir(self.srcdir)
                old_dest = listdir(realDest)
                old_cwd  = listdir(cwd)

                if verbosity == 2:
                    pass  # TODO: What do I do here?
                try:
                    tryExtract(self.srcfile, dest)
                except NoExtractorError:
                    self.skipTest("No suitable extractors installed")
                except UnsupportedFiletypeError:
                    self.skipTest("Unball doesn't know how to unpack this")
                callstring = "tryExtract(%r, %r)" % (self.srcfile, dest)

                if realDest == self.srcdir:
                    self.assertTrue(
                        len(listdir(self.srcdir)) > len(old_src),
                        "Callstring didn't extract to source dir: "
                        "%s" % callstring)
                else:
                    self.assertTrue(
                        len(listdir(self.srcdir)) == len(old_src),
                        "Callstring extracted ti source dir: "
                        "%s" % callstring)

                if realDest != cwd:
                    self.assertFalse(len(listdir(cwd))  > len(old_cwd),
                        "Callstring used working dir instead of explicit "
                        "destination: %s" % callstring)

                self.assertTrue(os.path.exists(self.srcfile),
                    "%s didn't preserve the original archive" % callstring)
                self.assertFalse(len(listdir(realDest)) < (len(old_dest) + 1),
                    "%s extract nothing to the target dir." % callstring)

                added_files = [x for x in listdir(realDest)
                               if x not in old_dest]
                newdir = os.path.join(realDest, added_files[0])
                if os.path.isdir(newdir):
                    self.assertFalse(len(listdir(newdir)) <= 1,
                        "%s created an unnecessary wrapper dir" % callstring)
                    self.assertFalse(newdir.endswith('.tar'),
                        "%s didn't strip .tar from the name of the newly "
                        "created dir. (%s)" % (callstring, newdir))
                    if not filename in count_omit:
                        self.assertFalse(len(listdir(newdir)) != 9,
                            "%s did not extract the correct number of files. "
                            "Got %s but expected %s" % (
                                callstring, len(listdir(newdir)), 9))
                else:
                    self.assertFalse(filename not in compress_only,
                        "Archive extracted a single file when a folder was "
                        "expected: %s -> %s" % (filename, newdir))
                pass
            finally:
                os.chdir(oldcwd)
        testMethod.__doc__ = (
            """Testing unball %s with %s destination""" % (filename, destName))
        setattr(UnballTestSet, 'test%s' % destName.capitalize(), testMethod)

    # Note: Implicit is only truly implicit when unball is run from the
    #       command-line. (The command-line code calls os.getcwdu() for dest)
    makeTestMethod('implicit', 'destdir', 'destdir', 'destdir')
    makeTestMethod('explicit', 'destdir', 'cwd_dir', 'destdir')
    makeTestMethod('same', None, 'cwd_dir', 'srcdir')
    return UnballTestSet

class GlobalTests(unittest.TestCase):
    """Tests which don't need to be run once per test file.
    @todo: Figure out if and how to cleanly non-hardcode the test source here
    """
    testdir = 'test sources'

    @unittest.expectedFailure
    def testExtensionCoverage(self):
        """Checking for extensions without testcases"""
        present = [os.path.splitext(x)[1].lower() for x
                   in listdir(self.testdir)]
        missing = [ext for ext in EXTENSIONS if not ext in present]
        missing.sort()
        self.assertFalse(missing, "The following supported extensions have no "
                         "testcases: %s" % ', '.join(missing))

    def testMimetypeCoverage(self):
        """Checking for mimetypes without tests (prone to false negatives)"""
        def isPresent(mime):
            if mimetype is None:
                return True  # This problem is caught elsewhere
            if isinstance(mimetype, basestring):
                return mimetype in present
            else:
                return all(x in present for x in mimetype)

        present_exts = [os.path.splitext(x)[1].lower() for
                        x in listdir(self.testdir)]

        present = []
        for ext in present_exts:
            mimetype = EXTENSIONS.get(ext, None)
            if mimetype is None:
                continue
            if isinstance(mimetype, basestring):
                present.append(mimetype)
            else:
                present.extend(mimetype)

        missing = [x for x in EXTENSIONS.values() if not isPresent(x)]
        self.assertFalse(missing, "The following supported mimetypes have no "
                         "testcases: %s" % ', '.join(missing))

    @unittest.expectedFailure
    def testSelfTests(self):
        """Running unball's internal self-tests"""
        self.assertTrue(self_test(silent=True),
            "Unball's internal self-tests reported errors")

    def _check_mimetype(self, mime, test):
        """Apply the provided function to a mimetype or list of mimetypes and
        return True via any()
        See L{testOrphanedExts} for usage."""
        if isinstance(mime, (tuple, list)):
            return any(self._check_mimetype(x, test) for x in mime)
        else:
            return test(mime)

    def testOrphanedExts(self):
        """Checking for orphaned extension-mime mappings"""
        orphaned_exts = [ext for ext in EXTENSIONS
                         if not self._check_mimetype(EXTENSIONS[ext],
                            lambda x: x in EXTRACTORS or
                                      x in FALLBACK_DESCRIPTIONS)]
        self.assertFalse(orphaned_exts, "EXTENSIONS lines must be paired with "
                         "EXTRACTORS or FALLBACK_DESCRIPTIONS lines:" +
                         '\n'.join('%s: %s' % (ext, EXTENSIONS[ext]) for
                             ext in orphaned_exts))

    @unittest.expectedFailure
    def testOrphanedMimes(self):
        """Checking for mimetypes without extension fallbacks"""
        # Find potentially-orphaned extensions in the extractors
        # (and discard potentials that are merely aliases for header-checking)
        orphan_mimes_pre = [mime for mime in EXTRACTORS
                            if not mime in EXTENSIONS.values()]
        orphan_mimes = []
        for mime in orphan_mimes_pre:
            _aliases = [x for x in EXTRACTORS if x != mime and
                        EXTRACTORS[x] is EXTRACTORS[mime]]
            if not [x for x in EXTENSIONS if
                    EXTENSIONS[x] in _aliases]:
                orphan_mimes.append(mime)

        # Add in any extensionless FALLBACK_DESCRIPTIONS entries.
        orphan_mimes += [mime for mime in FALLBACK_DESCRIPTIONS
                         if not mime in EXTENSIONS.values()]
        self.assertFalse(orphan_mimes, "Mimetypes without extension mappings "
                         "detected:" +
                         '\n'.join(orphan_mimes))

    def testExtensionCases(self):
        """Checking for extension mappings which use non-lowercase alphas"""
        upper_exts = [ext for ext in EXTENSIONS if ext.lower() != ext]
        self.assertFalse(upper_exts, "Extension mappings must be "
                         "case-insensitive. Violations detected:" +
                         '\n'.join("%s: %s" % (ext, EXTENSIONS[ext]) for
                             ext in upper_exts))

    def testMimetypeCases(self):
        """Checking for extractor/msg mappings using non-lowercase alphas"""
        upper_mimes = [mime for mime in EXTRACTORS.keys() +
                       FALLBACK_DESCRIPTIONS.keys() if
                       mime.lower() != mime]
        upper_mimes += [mime for mime in EXTENSIONS.values() if
                        self._check_mimetype(mime, lambda x: x.lower() != x)]
        self.assertFalse(upper_mimes, "Mimetype-extractor/message mappings "
                         "must be case-insensitive. Violations detected:" +
                         '\n'.join(upper_mimes))


def gen_dir_suite(path=None, verbosity=0):
    """Generate and run a set of tests for the given dir full of archives."""
    path = abspath(path or os.path.join(dirname(__file__), 'test sources'))
    print('Testing directory "%s" ...' % os.path.split(path)[1])

    # Ensure interactive test runs mimic CI servers a bit more
    if 'DISPLAY' in os.environ:
        del os.environ['DISPLAY']

    if not verbosity:
        print("NOTE: stdin, stdout, and stderr are closed for these tests. "
              "If extraction of ACE files freezes, it's a regression.")
    else:
        print("WARNING: Verbose output defeats a regression test for unace. "
              "Please also run this in non-verbose mode.")

    f = [os.path.join(path, arch) for arch in listdir(path)
         if not (os.path.isdir(arch)) and not arch in excluded]
    f.sort()
    for path in f:
        yield unittest.makeSuite(makeTests(path, verbosity))

if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option("-v", "--verbose", action="count", dest="verbosity",
        default=0, help="Increase the unit test framework's verbosity.")
    parser.add_option("--unball_verbose", action="count", default=0,
        dest="unball_verbosity", help="Pass through unball's output. Twice to "
             "trigger verbosity in unball. Note that this sacrifices one of "
             "the unace regression tests.")

    (opts, args) = parser.parse_args()

    print("Platform: %s" % (sys.platform,))
    try:
        print("uname: %s" % ' '.join(os.uname()))
    except AttributeError:
        try:
            print("Windows Version: %s" % (sys.getwindowsversion(),))
        except AttributeError:
            print("Detailed system version information unavailable")

    tests  = unittest.TestSuite([
        unittest.TestSuite(gen_dir_suite(args and args[0] or None,
                                    opts.unball_verbosity)),
        unittest.makeSuite(GlobalTests)
    ])

    tester = unittest.TextTestRunner(verbosity=opts.verbosity + 1)
    result = tester.run(tests)

    # Let Travis-CI know whether there was success or failure
    sys.exit(not result.wasSuccessful())
