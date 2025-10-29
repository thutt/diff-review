= Configuring Remote X. =

Basic knowledge of Remote X with SSH is assumed.  Configuring PyQT6 to
work with remote X may need extra packages installed.

When starting vrt, if the following error is generated, then additional packages are required.
```
Could not load the Qt platform plugin 'xcb'
```

The reason is that PyQt needs this library to be able to interact with
the remote X server.

== Installation. ==
On Ubuntu, install the following package after PyQt6 is installed.
```
$ sudo apt install libxcb-cursor0
```



