=Installation with Virtual Env.=

In cases where full installation of required components is not
possible, the use of venv is necessary.  This assumes that the
repository has been cloned and the current working directory is the
top level directory in the repository.

* First setup venv.
```
$ python3 -m venv .venv
```
* Activate the environment.  Be sure to use the appropriate script.
  For bash, use .venv/bin/activate, and for C shells use
  .venv/bin/activate.csh.
```
$ source .venv/bin/activate
```

* Install PyQt6.
```
$ pip install PyQt6
```

* Now source the aliases script.
```
$ source scripts.d/aliases
```
Installation and setup is now complete.  Moving forward, the venv
activation script and aliases scripts must be run to setup the
environment before running.