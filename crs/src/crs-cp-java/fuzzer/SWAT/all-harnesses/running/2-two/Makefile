CLASSPATH=".:../jars/*"

OBJECTS=JenkinsTwo_Concolic

all: $(OBJECTS).class

$(OBJECTS).class: $(OBJECTS).java
	javac -cp $(CLASSPATH) -g $<

clean:
	rm -rf *.class
