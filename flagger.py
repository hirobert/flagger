import re
import json

def flask_to_swagger(app, groups=[]):
	app_dict = {}
	for rule in app.url_map.iter_rules():
		url = str(rule)
		resource_path_regex = re.compile('^/(?P<name>\w+)')
		resource_matches = resource_path_regex.findall(url)
		if resource_matches:
			resource_match = '/' + resource_matches[0]
			if groups:
				matches = False
				for group in groups:
					url_regex = re.compile(group)
					matches = url_regex.findall(url)
					if matches:
						if resource_match in app_dict:
							app_dict[resource_match].append(generate_configuration(app, rule))
						else:
							app_dict[resource_match] = [generate_configuration(app, rule)]
			else:
				if resource_match in app_dict:
					app_dict[resource_match].append(generate_configuration(app, rule))
				else:
					app_dict[resource_match] = [generate_configuration(app, rule)]
	bundle_to_json(app_dict)

def bundle_to_json(app_dict):
	for key in app_dict:
		file_json = {
			'apiVersion': '1.0.0',
			'swaggerVersion': '1.2',
			'basePath': ':5000',
			'resourcePath': key,
			'produces': [
				'application/json'
			],
			'apis': []
		}
		for url_json in app_dict[key]:
			for url_key in url_json:
				file_json['apis'].append(url_json[url_key])
		with open('%s.json' % key[1:], 'w') as outfile:
			json.dump(file_json, outfile, indent=4)


def generate_configuration(app, rule):
	url_dict = {}
	url = str(rule)
	#variables = rule.arguments
	endpoint_method = rule.endpoint
	http_methods = list(rule.methods.difference(['OPTIONS', 'HEAD']))
	view = app.view_functions[endpoint_method]
	docstring = view.__doc__ or ''
	docstring_dict = parse_docstring(docstring)
	for http_method in http_methods:
		rule_dict = {
			'method': http_method,
			'summary': '',
			'notes': '\n'.join(docstring_dict['lines']),
			'nickname': camel_case(endpoint_method),
			'parameters': docstring_dict['vars']
		}
		if url in url_dict:
			if 'operations' in url_dict[url]:
				url_dict[url]['operations'].append(rule_dict)
			else:
				url_dict[url]['operations'] = [rule_dict]
		else:
			url_dict[url] = {
				'path': url,
				'operations': [rule_dict]
			}
	return url_dict

def camel_case(stringy):
	stringy = stringy.replace('_', ' ')
	stringy_split_up = stringy.split()
	for index in range(1, len(stringy_split_up)):
		#dont capitalize first one
		stringy_split_up[index] = stringy_split_up[index].capitalize()
	camel_case_string = ''.join(stringy_split_up)
	return camel_case_string

def parse_docstring(docstring):
	docstring_dict = {
		'lines': [],
		'vars': []
	}
	for line in docstring.splitlines():
		line = line.strip()
		if line:
			arg_regex = re.compile('^:arg (?P<type>\w+)? (?P<param>\w+): (?P<doc>.*)$')
			arg_tuple = arg_regex.findall(line)
			if arg_tuple:
				for var_tuple in arg_tuple:
					var_type, var_name, var_desc = var_tuple
					var_dict = {
						'name': var_name,
						'description': var_desc,
						'required': True,
						'type': var_type,
						'paramType': 'path',
						'allowMultiple': False
					}
					docstring_dict['vars'].append(var_dict)
			else:
				docstring_dict['lines'].append(line)
	return docstring_dict


if __name__ == '__main__':
	import sys, os
	sys.path.insert(0, os.path.abspath('../../Noun-API/app/'))

	from noun import create_app
	app = create_app()

	#generate configurations
	flask_to_swagger(app, ['/collection/'])