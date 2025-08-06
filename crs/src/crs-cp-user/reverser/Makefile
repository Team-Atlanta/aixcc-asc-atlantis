usage:
	@echo "Usage: make [command]"
	@echo ""
	@echo "Commands:"
	@echo "  run [file=filename]  Run the program with the specified file"
	@echo "  verify               Verify the syntax of the answer files"

# Takes an argument of a file to run ./run.py on
# Verify the correct number of arguments are passed
run:
ifndef file
	@echo "Usage: make run [file=filename]"
	$(error Usage: make run [file=filename])
endif
	python ./run.py $(file)

demo:
	python ./run.py ./linux_test_harness.c

verify:
	python ./tools/verify_answer_syntax.py