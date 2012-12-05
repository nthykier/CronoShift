"""
@copyright: 2012, Niels Thykier <niels@thykier.net>
@license:
Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions
are met:

 * Redistributions of source code must retain the above copyright
   notice, this list of conditions and the following disclaimer.

 * Redistributions in binary form must reproduce the above copyright
   notice, this list of conditions and the following disclaimer in
   the documentation and/or other materials provided with the
   distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
"AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED
TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""
import itertools
import os

class JikibanCampaign(object):

    def __init__(self):
        self._dirname = ""
        self._level_names = []

    def load_campaign(self, fname, infd=None, leveldir=None):
        if infd is None:
            with open(fname) as fd:
                return self.load_campaign(fname, infd=fd, leveldir=leveldir)

        dirname = leveldir
        if dirname is None:
            dirname = os.path.dirname(fname)

        lineiter = itertools.imap(lambda x: x.rstrip("\r\n"), infd)

        header = next(lineiter, 1)
        if header != "JikiBan Campaign":
            raise IOError("Bad header of %s" % fname)

        # Ignore empty and "#"-comments
        filt = lambda x: x != "" and x[0] != "#"

        level_names = filter(filt, lineiter)

        for lvl in level_names:
            if os.path.isabs(lvl):
                raise IOError("Campaign file %s uses absolute filename %s" \
                                  % (fname, lvl))
            if not os.path.exists(os.path.join(dirname, lvl)):
                raise IOError("Campaign file %s refers to non-existent file %s" \
                                  % (fname, lvl))

        self._level_names = level_names
        self._dirname = dirname

    def save_campaign(self, fname, fd=None):
        if fd is None:
            with open(fname, "w") as outfd:
                return self.save_campaign(fname, fd=outfd)
        fd.write("JikiBan Campaign\n\n")
        fd.write("\n".join(self._level_names))
        fd.write("\n")

    def __len__(self):
        return len(self._level_names)

    def __getitem__(self, index):
        return os.path.join(self._dirname, self._level_names[index])

