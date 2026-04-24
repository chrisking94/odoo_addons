# -*- coding: utf-8 -*-
# @Time         : 10:26 2026/4/24
# @Author       : Chris
# @Description  :
import json

from odoo import http
from odoo.http import request, Root, HttpRequest
from werkzeug.wrappers import Response as WerkzeugResponse


# ---- Monkey Patch Start ----
# Odoo Controller is strict to request type and endpoint type.
# We need to make a monkey patch to loose this restriction for mcp endpoint.
# This patch wrap all request to mcp endpoint as HTTPRequest, then controller will handle http request manually,
# no matter it is http or json request.
_original_get_request = Root.get_request


def _patched_get_request(self, httprequest):
    if httprequest.path == '/mcp':
        return HttpRequest(httprequest)
    return _original_get_request(self, httprequest)


Root.get_request = _patched_get_request
# ---- Monkey Patch End ---


class McpController(http.Controller):

    @http.route('/mcp', type='http', auth='public', csrf=False, methods=['GET', 'POST'])
    def mcp_endpoint(self, **kwargs):
        """
        Unified Streamable HTTP endpoint for MCP protocol.
        
        GET  → SSE stream for server notifications
        POST → JSON-RPC message handling
        """
        if request.httprequest.method == 'GET':
            return self._handle_sse_stream()
        elif request.httprequest.method == 'POST':
            return self._handle_json_rpc()
        else:
            return WerkzeugResponse('Method Not Allowed', status=405)

    def _handle_sse_stream(self):
        """Handle GET request - establish SSE stream."""
        def stream():
            yield "event: endpoint\ndata: /mcp\n\n"

        return WerkzeugResponse(
            stream(),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'X-Accel-Buffering': 'no',
                'Access-Control-Allow-Origin': '*',
            }
        )

    def _handle_json_rpc(self):
        """Handle POST request - process JSON-RPC messages."""
        try:
            payload = json.loads(request.httprequest.get_data(as_text=True))
            
            result = self._process_mcp_method(
                payload.get('method'),
                payload.get('params', {})
            )
            
            return self._json_response({
                "jsonrpc": "2.0",
                "id": payload.get('id'),
                "result": result
            })

        except json.JSONDecodeError:
            return self._json_response({
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": "Parse error"}
            }, 400)
            
        except Exception as e:
            import traceback
            print(f"[MCP] Error: {e}\n{traceback.format_exc()}")
            
            return self._json_response({
                "jsonrpc": "2.0",
                "id": payload.get('id') if 'payload' in locals() else None,
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}",
                    "data": traceback.format_exc()
                }
            }, 500)

    def _json_response(self, data, status=200):
        """Create JSON response with CORS headers."""
        return WerkzeugResponse(
            json.dumps(data, ensure_ascii=False),
            status=status,
            mimetype='application/json',
            headers={'Access-Control-Allow-Origin': '*'}
        )

    def _process_mcp_method(self, method, params):
        """Route MCP method to handler."""
        handlers = {
            'initialize': self._handle_initialize,
            'tools/list': self._handle_list_tools,
            'tools/call': self._handle_call_tool,
        }
        
        handler = handlers.get(method)
        if not handler:
            raise Exception(f"Method not found: {method}")
        
        return handler(params)
    
    def _handle_initialize(self, params):
        """Handle initialize request."""
        return {
            "protocolVersion": "2025-03-26",
            "capabilities": {"tools": {}},
            "serverInfo": {
                "name": "Odoo-MCP-Server",
                "version": "1.0.0"
            }
        }
    
    def _handle_list_tools(self, params):
        """Handle tools/list request."""
        tools = []
        
        for model_name, model_obj in request.env.registry.models.items():
            for attr_name in dir(model_obj):
                if attr_name.startswith('_'):
                    continue
                    
                try:
                    method = getattr(model_obj, attr_name)
                    if callable(method) and getattr(method, '_is_mcp_tool', False):
                        tools.append({
                            "name": f"{model_name}:{attr_name}",
                            "description": getattr(method, '_mcp_desc', ""),
                            "inputSchema": getattr(method, '_mcp_schema', {"type": "object"})
                        })
                except:
                    continue
        
        print(f"[MCP] Found {len(tools)} tools")
        return {"tools": tools}
    
    def _handle_call_tool(self, params):
        """Handle tools/call request."""
        name = params.get('name')
        arguments = params.get('arguments', {})
        
        try:
            model_name, method_name = name.split(':')
            model = request.env[model_name].sudo()
            result = getattr(model, method_name)(**arguments)
            
            return {
                "content": [{
                    "type": "text",
                    "text": json.dumps(result) if not isinstance(result, str) else result
                }]
            }
            
        except Exception as e:
            import traceback
            print(f"[MCP] Tool error: {e}\n{traceback.format_exc()}")
            
            return {
                "content": [{"type": "text", "text": f"Error: {str(e)}"}],
                "isError": True
            }
