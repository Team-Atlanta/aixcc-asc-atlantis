CLASSPATH=".:../jars/*"

OBJECTS=JenkinsFourConcolic

all: $(OBJECTS).class

$(OBJECTS).class: $(OBJECTS).java
	javac -cp $(CLASSPATH) -g $<

clean:
	rm -rf *.class
