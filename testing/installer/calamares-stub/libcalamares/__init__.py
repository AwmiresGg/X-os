# Minimal stand-in for Calamares' libcalamares, enough to run Python job modules offline.
class _U:
    def debug(self, *a): pass
    def warning(self, *a): print("WARN", *a)
    def host_env_process_output(self, *a, **k): pass
    def gettext_path(self): return None
    def gettext_languages(self): return []
utils = _U()
class _J:
    configuration = {}
    def setprogress(self, p): pass
job = _J()
globalstorage = None
