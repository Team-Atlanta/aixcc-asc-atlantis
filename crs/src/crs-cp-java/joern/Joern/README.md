
# Joern for AIxCC

This repository is for any modification to Joern (@f1221 main/origin) for the purpose of AIxCC.

## Building Joern 

Install sbt module and the run 

`sbt stage`

## Wrapper

This is a custom folder to combine two different projects
(this is on hold due to another workaround).

## autoScripts

Scripts under this folder are ment automatically performing the following queries:
1. listing the test files under exemplar 
2. listing the jenkins methods being called in these test files.


#### TODO
1. query to load the node from source after obtaining the function of interest from exemplar.
2. Generating the CFG, PDG, DFG based on the previous query.

