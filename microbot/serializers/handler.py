from rest_framework import serializers
from microbot.models import Handler, Request, Response, UrlParam, HeaderParam, State
from microbot.serializers import StateSerializer, ResponseSerializer, ResponseUpdateSerializer

class AbsParamSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    
    class Meta:
        model = UrlParam
        fields = ('id', 'created_at', 'updated_at', 'key', 'value_template')      
        read_only_fields = ('id', 'created_at', 'updated_at',)  
        
class RequestSerializer(serializers.HyperlinkedModelSerializer):
    url_parameters = AbsParamSerializer(many=True, required=False)
    header_parameters = AbsParamSerializer(many=True, required=False)
    
    class Meta:
        model = Request
        fields = ('url_template', 'method', 'data', 'url_parameters', 'header_parameters')
        
class RequestUpdateSerializer(RequestSerializer):
    url_template = serializers.CharField(required=False, max_length=255)
    method = serializers.ChoiceField(choices=Request.METHOD_CHOICES, required=False)


class HandlerSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField()
    request = RequestSerializer(many=False, required=False)
    response = ResponseSerializer(many=False)
    target_state = StateSerializer(many=False, required=False)
    source_states = StateSerializer(many=True, required=False)
    priority = serializers.IntegerField(required=False)

    class Meta:
        model = Handler
        fields = ('id', 'created_at', 'updated_at', 'name', 'pattern', 'enabled', 'request', 'response', 'target_state', 'source_states', 'priority')
        read_only = ('source_states', 'id', 'created_at', 'updated_at',)
        
    def _create_params(self, params, model, request):
        for param in params:
            model.objects.get_or_create(key=param['key'],
                                        value_template=param['value_template'],
                                        request=request)  
                
    def _update_params(self, params, query_get):
        for param in params:
            instance_param = query_get(key=param['key'])
            instance_param.key = param['key']
            instance_param.value_template = param['value_template']
            instance_param.save()
                   
    def create(self, validated_data):
        state = None
        request = None
        if 'target_state' in validated_data:
            state, _ = Request.objects.get_or_create(**validated_data['target_state'])
        if 'request' in validated_data:
            request, _ = Request.objects.get_or_create(**validated_data['request'])
            self._create_params(validated_data['request']['url_parameters'], UrlParam, request)
            self._create_params(validated_data['request']['header_parameters'], HeaderParam, request)
            
        response, _ = Response.objects.get_or_create(**validated_data['response'])
        
        handler, _ = Handler.objects.get_or_create(pattern=validated_data['pattern'],
                                                   response=response,
                                                   enabled=validated_data['enabled'],
                                                   request=request,
                                                   target_state=state,
                                                   priority=validated_data.get('priority', 0))
        
        return handler
    
    def update(self, instance, validated_data):
        instance.name = validated_data.get('name', instance.name)
        instance.pattern = validated_data.get('pattern', instance.pattern)
        instance.enabled = validated_data.get('enabled', instance.enabled)
        instance.priority = validated_data.get('priority', instance.priority)
        if 'target_state' in validated_data:
            state, _ = State.objects.get_or_create(bot=instance.bot,
                                                   name=validated_data['target_state']['name'])
            instance.target_state = state
        if 'response' in validated_data:
            instance.response.text_template = validated_data['response'].get('text_template', instance.response.text_template)
            instance.response.keyboard_template = validated_data['response'].get('keyboard_template', instance.response.keyboard_template)
            instance.response.save()

        if 'request' in validated_data:
            instance.request.url_template = validated_data['request'].get('url_template', instance.request.url_template)
            instance.request.method = validated_data['request'].get('method', instance.request.method)
            instance.request.data = validated_data['request'].get('data', instance.request.data)
            instance.request.save()
        
            if 'url_parameters' in validated_data['request']:
                self._update_params(validated_data['request']['url_parameters'], instance.request.url_parameters.get)
            if 'header_parameters' in validated_data['request']:
                self._update_params(validated_data['request']['header_parameters'], instance.request.header_parameters.get)
            
        instance.save()
        return instance
    
class HandlerUpdateSerializer(HandlerSerializer):
    name = serializers.CharField(required=False, max_length=100)
    pattern = serializers.CharField(required=False, max_length=250)
    priority = serializers.IntegerField(required=False, min_value=0)
    response = ResponseUpdateSerializer(many=False, required=False)
    request = RequestUpdateSerializer(many=False, required=False)    