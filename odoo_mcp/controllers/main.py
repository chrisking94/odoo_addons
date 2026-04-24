# -*- coding: utf-8 -*-
# @Time         : 10:26 2026/4/24
# @Author       : Chris
# @Description  :
import json

from odoo import http
from odoo.http import request
from werkzeug.wrappers import Response as WerkzeugResponse


class McpController(http.Controller):

    @http.route('/mcp/sse', type='http', auth='public', csrf=False)
    def sse_endpoint(self, **kwargs):
        """Handles the SSE Handshake."""
        if request.httprequest.method == 'OPTIONS':
            return WerkzeugResponse(
                '',
                status=200,
                headers=[
                    ('Access-Control-Allow-Origin', '*'),
                    ('Access-Control-Allow-Methods', 'GET, OPTIONS'),
                    ('Access-Control-Allow-Headers', 'Content-Type'),
                    ('Content-Length', '0'),
                ]
            )
        
        msg_url = f"{request.httprequest.host_url}mcp/message"

        def stream():
            yield f"event: endpoint\ndata: {msg_url}\n\n"

        return WerkzeugResponse(
            stream(),
            mimetype='text/event-stream',
            headers=[
                ('Cache-Control', 'no-cache'),
                ('Connection', 'keep-alive'),
                ('X-Accel-Buffering', 'no'),
                ('Access-Control-Allow-Origin', '*'),
            ]
        )

    @http.route('/mcp/message', type='json', auth='public', csrf=False)
    def message_handler(self, **kwargs):
        """Handles MCP JSON-RPC messages."""
        try:
            payload = request.jsonrequest
            request_id = payload.get('id')
            method = payload.get('method')
            params = payload.get('params', {})
            
            # Route to appropriate handler
            if method == 'initialize':
                result = self._handle_initialize(params)
            elif method == 'tools/list':
                result = self._handle_list_tools()
            elif method == 'tools/call':
                result = self._handle_call_tool(params)
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}"
                    }
                }
            
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result
            }

        except Exception as e:
            import traceback
            return {
                "jsonrpc": "2.0",
                "id": request.jsonrequest.get("id") if hasattr(request, 'jsonrequest') and request.jsonrequest else None,
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}",
                    "data": traceback.format_exc()
                }
            }
    
    def _handle_initialize(self, params):
        """Handle initialize request."""
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {}
            },
            "serverInfo": {
                "name": "Odoo-MCP-Server",
                "version": "1.0.0"
            }
        }
    
    def _handle_list_tools(self):
        """Handle tools/list request."""
        tools = []
        for model_name, model_obj in request.env.registry.models.items():
            for attr_name in dir(model_obj):
                method = getattr(model_obj, attr_name)
                if getattr(method, '_is_mcp_tool', False):
                    tools.append({
                        "name": f"{model_name}.{attr_name}",
                        "description": getattr(method, '_mcp_desc', ""),
                        "inputSchema": getattr(method, '_mcp_schema', {"type": "object"})
                    })
        return {"tools": tools}
    
    def _handle_call_tool(self, params):
        """Handle tools/call request."""
        name = params.get('name')
        arguments = params.get('arguments', {})
        
        try:
            model_name, method_name = name.split('.')
            model = request.env[model_name].sudo()
            result = getattr(model, method_name)(**arguments)
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result) if not isinstance(result, str) else result
                    }
                ]
            }
        except Exception as e:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error: {str(e)}"
                    }
                ],
                "isError": True
            }
