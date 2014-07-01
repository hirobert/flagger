import re
import json

def flask_to_swagger(app, groups=[], allowed_methods=[]):
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
                        if not allowed_methods:
                            if resource_match in app_dict:
                                app_dict[resource_match].append(generate_configuration(app, rule))
                            else:
                                app_dict[resource_match] = [generate_configuration(app, rule)]
                        elif rule.endpoint in allowed_methods:
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
    generate_api_doc(app_dict)

def bundle_to_json(app_dict):
    #bundle and write file
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
    #modify url for swagger spec
    #/example/<string:variable_name> becomes /example/{variable_name}
    url_var_regex = re.compile('(<\w+[:\w+]*>)')
    url_re_matches = url_var_regex.findall(url)
    if url_re_matches:
        for url_re_match in url_re_matches:
            new_url_var = url_re_match
            if ':' in new_url_var:
                new_url_var = new_url_var[new_url_var.index(':'):len(new_url_var)]
                new_url_var = new_url_var.replace(':', '<')
            new_url_var = new_url_var.replace('<', '{')
            new_url_var = new_url_var.replace('>', '}')
            url = url.replace(url_re_match, new_url_var)
    #variables = rule.arguments
    endpoint_method = rule.endpoint
    http_methods = list(rule.methods.difference(['OPTIONS', 'HEAD']))
    view = app.view_functions[endpoint_method]
    docstring = view.__doc__ or ''
    docstring_dict = parse_docstring(docstring)
    #set up configuration
    for http_method in http_methods:
        rule_dict = {
            'method': http_method,
            'summary': endpoint_method.replace('_', ' ').capitalize(),
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
    #turns strings to camel case
    #get_user_by_id becomes getUserById
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
            #this is our "halt" flag, in the docs
            #feel free to set your own in the docstrings
            #and don't forget change the regex to match!
            stop_regex = re.compile('^`Try it out!')
            if stop_regex.findall(line):
                break
            #We haven't reached the break point yet, process the docstrings
            arg_regex = re.compile('^:(arg|argument|param|parameter|query) (?P<type>\w+)? (?P<param>\w+): (?P<doc>.*)$')
            arg_tuple = arg_regex.findall(line)
            if arg_tuple:
                for var_tuple in arg_tuple:
                    var_arg, var_type, var_name, var_desc = var_tuple
                    var_dict = {
                        'name': var_name,
                        'description': var_desc.capitalize(),
                        'required': True,
                        'type': var_type,
                        'paramType': 'path',
                        'allowMultiple': False
                    }
                    #modifications for query strings
                    if var_arg == 'query':
                        var_dict['paramType'] = 'query'
                        var_dict['required'] = False
                    docstring_dict['vars'].append(var_dict)
            else:
                docstring_dict['lines'].append(line)

    return docstring_dict

def generate_api_doc(route_dict):
    api_doc_json = {
        "apiVersion": "1.0.0",
        "swaggerVersion": "1.2",
        "apis": []
    }
    for method in route_dict:
        path = method
        name = method[1:]
        endpoint_json = {
            "path": path,
            "description": "Operations on {} endpoints".format(name)
        }
        api_doc_json['apis'].append(endpoint_json)

    with open('api-doc.json', 'w') as outfile:
        json.dump(api_doc_json, outfile, indent=4)

if __name__ == '__main__':
    import sys, os
    app_directory = '../'
    sys.path.insert(0, os.path.abspath(app_directory))

    from your_app import app

    endpoint_groups = ['/user/', '/users/', '/collection/']
    endpoint_methods = [
            'get_user_by_id', 'get_user_by_username',
            'get_all_users', 'get_recent_users',
            'get_collection_by_id', 'get_collection_by_slug'
        ]

    #generate configurations
    flask_to_swagger(app, groups=endpoint_groups, allowed_methods=endpoint_methods)
