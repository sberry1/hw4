p1:
	cp alu.circ alu-control.circ tests
	cd tests && python3 ./test.py | tee ../TEST_LOG
