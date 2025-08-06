CLASSPATH=".:../jars/*"

OBJECTS=JenkinsFourteen_Concolic

all: $(OBJECTS).class

$(OBJECTS).class: $(OBJECTS).java
	javac -cp $(CLASSPATH) -g $<

run:
	java -cp $(CLASSPATH) $(OBJECTS) init.value

clean:
	rm -rf *.class
