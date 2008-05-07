import mimetypes
import re
import time
from actor import Actor
from commit import Commit

class Blob(object):
    DEFAULT_MIME_TYPE = "text/plain"
    
    def __init__(self, repo, **kwargs):
        """
        Create an unbaked Blob containing just the specified attributes
        
        ``repo`` 
            is the Repo
        
        ``atts``
            is a dict of instance variable data

        Returns
            GitPython.Blob
        """
        self.id = None
        self.mode = None
        self.name = None
        self.size = None
        self.data_stored  = None
        
        self.repo = repo
        for k, v in kwargs.items():
            setattr(self, k, v)
    
    def __len__(self):
        """
        The size of this blob in bytes

        Returns
            int
        """
        self.size = self.size or int(self.repo.git.cat_file(self.id, **{'s': True}).rstrip())
        return self.size
    
    @property
    def data(self):
        """
        The binary contents of this blob.

        Returns
            str
        """
        self.data_stored = self.data_stored or self.repo.git.cat_file(self.id, **{'p': True})
        return self.data_stored

    @property
    def mime_type(self):
        """
        The mime type of this file (based on the filename)

        Returns
            str
        """
        guesses = None
        if self.name:
            guesses = mimetypes.guess_type(self.name)
        return guesses and guesses[0] or self.DEFAULT_MIME_TYPE
    
    @property
    def basename(self):
      return os.path.basename(self.name)

    @classmethod
    def blame(cls, repo, commit, file):
        """
        The blame information for the given file at the given commit

        Returns
            list: [GitPython.Commit, list: [<line>]]
        """
        data = repo.git.blame(commit, '--', file, **{'p': True})
        commits = {}
        blames = []
        info = None
        
        for line in data.splitlines():
            parts = re.split(r'\s+', line, 1)
            if re.search(r'^[0-9A-Fa-f]{40}$', parts[0]):
                if re.search(r'^([0-9A-Fa-f]{40}) (\d+) (\d+) (\d+)$', line):
                    m = re.search(r'^([0-9A-Fa-f]{40}) (\d+) (\d+) (\d+)$', line)
                    id, origin_line, final_line, group_lines = m.groups()
                    info = {'id': id}
                    blames.append([None, []])
                elif re.search(r'^([0-9A-Fa-f]{40}) (\d+) (\d+)$', line):
                    m = re.search(r'^([0-9A-Fa-f]{40}) (\d+) (\d+)$', line)
                    id, origin_line, final_line = m.groups()
                    info = {'id': id}
            elif re.search(r'^(author|committer)', parts[0]):
                if re.search(r'^(.+)-mail$', parts[0]):
                    m = re.search(r'^(.+)-mail$', parts[0])
                    info["%s_email" % m.groups()[0]] = parts[-1]
                elif re.search(r'^(.+)-time$', parts[0]):
                    m = re.search(r'^(.+)-time$', parts[0])
                    info["%s_date" % m.groups()[0]] = time.gmtime(int(parts[-1]))
                elif re.search(r'^(author|committer)$', parts[0]):
                    m = re.search(r'^(author|committer)$', parts[0])
                    info[m.groups()[0]] = parts[-1]
            elif re.search(r'^filename', parts[0]):
                info['filename'] = parts[-1]
            elif re.search(r'^summary', parts[0]):
                info['summary'] = parts[-1]
            elif parts[0] == '':
                if info:
                    c = commits.has_key(info['id']) and commits[info['id']]
                    if not c:
                        c = Commit(repo, **{'id': info['id'],
                                            'author': Actor.from_string(info['author'] + ' ' + info['author_email']),
                                            'authored_date': info['author_date'],
                                            'committer': Actor.from_string(info['committer'] + ' ' + info['committer_email']),
                                            'committed_date': info['committer_date'],
                                            'message': info['summary']})
                        commits[info['id']] = c
                
                    m = re.search(r'^\t(.*)$', line)
                    text,  = m.groups()
                    blames[-1][0] = c
                    blames[-1][1] += text
                    info = None
      
        return blames
    
    def __repr__(self):
        return '<GitPython.Blob "%s">' % self.id
