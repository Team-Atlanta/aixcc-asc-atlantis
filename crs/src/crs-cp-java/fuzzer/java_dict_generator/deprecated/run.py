from py4j.java_gateway import JavaGateway

inputs = [
	('id1', 'PipelineCommandUtilFuzzer_Fuzz'),
	('id3', 'ProxyConfigurationFuzzer_Fuzz'),
	('id4', 'CoverageProcessorFuzzer_Fuzz'),
	('id5', 'UserNameActionFuzzer_Fuzz'),
	('id6', 'StateMonitorFuzzer_Fuzz'),
	('id7', 'UserRemoteConfigFuzzer_Fuzz'),
	('id8', 'AuthActionFuzzer_Fuzz'),
	('id9', 'ApiFuzzer_Fuzz'),
	('id10', 'SecretMessageFuzzer_Fuzz'),
	('id11', 'AccessFilterFuzzer_Fuzz'),
]

def one_dict_gen(gateway, id, classname):
	global inputs

	try:
		print(f'Running {classname}...')
		gateway.entry_point.generate(classname, 'fuzzerTestOneInput', f'test/{id}/fuzz.dict')
		print(f'Finished {classname}...')
	except Exception as e:
		print(f'Error: {e}')


def main():
	gateway = JavaGateway()
	for id, classname in inputs:
		one_dict_gen(gateway, id, classname)

if __name__ == '__main__':
	main()