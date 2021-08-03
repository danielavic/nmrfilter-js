build:
	docker build -t nmrfilter .

bash:
	docker run -it -p 5040:5040 --rm -v $(shell pwd):/home/nmrfilter --name nmrfilter nmrfilter bash

interactive:
	docker run -it -p 5040:5040 --rm -v $(shell pwd):/home/nmrfilter --name nmrfilter nmrfilter sh /home/nmrfilter/run_server.sh

server:
	docker run -itd -p 5040:5040 --rm -v $(shell pwd):/home/nmrfilter --name nmrfilter nmrfilter sh /home/nmrfilter/run_server.sh
