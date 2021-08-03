# NMRfilter 
<p align="center">
  <img src="https://github.com/computational-chemical-biology/nmrfilter/blob/master/nmrfilter_viewer/api/static/img/nmrfilter.gif?raw=true" alt="nmrfilter logo"/>
</p>

NMRfilter: compound identification based on chemical shift predictions. Please cite [Metabolomics volume 16, Article number: 123 (2020)](https://doi.org/10.1007/s11306-020-01748-1)

### Installation
```
git clone https://github.com/computational-chemical-biology/nmrfilter.git
```
### Docker

Docker provides the ability to package and run an application in a loosely isolated environment called a container. [Click here to find more about this topic](https://docs.docker.com/get-started/overview/)

* [Install Docker](https://docs.docker.com/engine/install/ubuntu/).

### Makefile 

Automation tool to run and compile your programs. [Click here to find more about this topic](https://opensource.com/article/18/8/what-how-makefile)

Inside the nmrfilter_viewer folder, there is a "Makefile" text file:

```
build:
	docker build -t nmrfilter .

bash:
	docker run -it -p 5040:5040 --rm -v $(shell pwd):/home/nmrfilter --name nmrfilter nmrfilter bash

interactive:
	docker run -it -p 5040:5040 --rm -v $(shell pwd):/home/nmrfilter --name nmrfilter nmrfilter sh /home/nmrfilter/run_server.sh

server:
	docker run -itd -p 5040:5040 --rm -v $(shell pwd):/home/nmrfilter --name nmrfilter nmrfilter sh /home/nmrfilter/run_server.sh
```

In the terminal command line, go to the nmrfilter_viewer folder:

```
cd nmrfilter/nmrfilter_viewer
```

So, do the following commands:

```
make build 
make interactive
```

A message like this will appear:

```
docker run -it -p 5040:5040 --rm -v /home/nmrfilter/nmrfilter_viewer:/home/nmrfilter --name nmrfilter nmrfilter sh /home/nmrfilter/run_server.sh
[2021-06-21 22:29:58 +0000] [8] [INFO] Starting gunicorn 20.1.0
[2021-06-21 22:29:58 +0000] [8] [INFO] Listening at: http://0.0.0.0:5040 (8)
[2021-06-21 22:29:58 +0000] [8] [INFO] Using worker: sync

```
Through the link you can access the application: 

```
Listening at:http://0.0.0.0:5040
```
Then add '/nmrfilter' to the url: 

```
http://0.0.0.0:5040/nmrfilter
```
Done! It is now possible to run the application.

### Note

Depending on the path where the application was saved, it may be necessary to modify the 'nmrproc.properties' file. If this is your case:

Open the 'nmrproc.properties' file and, on the following line:

```
datadir=/home/nmrfilter/api 
```
Change to the correct path on your computer.

### References

* https://docs.docker.com/get-started/overview/
* https://docs.docker.com/engine/install/ubuntu/
* https://opensource.com/article/18/8/what-how-makefile
