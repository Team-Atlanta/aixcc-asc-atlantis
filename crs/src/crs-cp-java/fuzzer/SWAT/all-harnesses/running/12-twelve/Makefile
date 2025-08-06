CLASSPATH=".:../jars/*"

OBJECTS=JenkinsTwelve_Concolic

all: $(OBJECTS).class

$(OBJECTS).class: $(OBJECTS).java
	javac -cp $(CLASSPATH) -g $<

run:
	java -cp $(CLASSPATH) $(OBJECTS) init.value

clean:
	rm -rf *.class
