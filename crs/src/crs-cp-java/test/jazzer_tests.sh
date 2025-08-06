/classpath/jazzer/jazzer --help \
            --agent_path=/classpath/jazzer/jazzer_standalone_deploy.jar \
            "--cp=$CLASSPATH:$DEST:/root/.m2/repository/org/kohsuke/stapler/stapler/1822.v120278426e1c/stapler-1822.v120278426e1c.jar:$SRC/javax.servlet-api-4.0.1.jar" \
            --jvm_args="-Djdk.attach.allowAttachSelf=true:-Djenkins.security.ClassFilterImpl.SUPPRESS_ALL=true:-XX\:+StartAttachListener"

            #-runs=1 \
            #--target_class=$CLASS_NAME \
            #-artifact_prefix=$REPRODUCER_DIR/ \
            #--reproducer_path=$REPRODUCER_DIR \
