import json
import os

def test_model_profiles_are_valid():
    """
    Tests that all models in the default profiles of api_providers.json are valid models
    in model_list.json.
    """
    # Construct absolute paths to the JSON files
    current_dir = os.path.dirname(os.path.abspath(__file__))
    api_providers_path = os.path.join(current_dir, '..', 'src', 'jrdev', 'config', 'api_providers.json')
    model_list_path = os.path.join(current_dir, '..', 'src', 'jrdev', 'config', 'model_list.json')

    # Load the JSON files
    with open(api_providers_path, 'r') as f:
        api_providers = json.load(f)
    with open(model_list_path, 'r') as f:
        model_list = json.load(f)

    # Extract all model names from api_providers.json
    provider_models = []
    for provider in api_providers['providers']:
        if 'default_profiles' in provider and 'profiles' in provider['default_profiles']:
            provider_models.extend(provider['default_profiles']['profiles'].values())

    # Extract all valid model ids from model_list.json
    # The model list can have 'id' or 'name' for the model identifier. Let's check for both.
    valid_model_ids = set()
    if 'models' in model_list:
        for model in model_list['models']:
            if 'id' in model:
                valid_model_ids.add(model['id'])
            if 'name' in model:
                valid_model_ids.add(model['name'])


    # Check that each provider model is in the valid model list
    for model_name in provider_models:
        assert model_name in valid_model_ids, f"Model '{model_name}' not found in model_list.json"
