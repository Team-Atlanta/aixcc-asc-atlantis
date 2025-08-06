#!/bin/bash
gradle copyNativeLibs
gradle build -x test

