import re

with open('C:/Users/ACER/Documents/GitHub/SoftwareHorasMonitores/apps/work_sessions/api/views.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add invalidate_work_session to imports
content = content.replace(
    'from apps.work_sessions.services import review_overtime',
    'from apps.work_sessions.services import review_overtime, invalidate_work_session\nfrom rest_framework import serializers'
)

# Add the endpoint to the ViewSet
new_endpoint = """
    @decorators.action(detail=True, methods=["post"], url_path="invalidate")
    def invalidate_action(self, request, pk=None):
        session = self.get_object()
        reason = request.data.get("reason", "").strip()
        if not reason:
            raise exceptions.ValidationError("Se requiere un motivo para invalidar la sesión.")
        try:
            invalidate_work_session(session=session, actor=request.user, reason=reason)
        except DjangoValidationError as exc:
            raise exceptions.ValidationError(exc.messages)
        return response.Response(WorkSessionSerializer(session).data, status=status.HTTP_200_OK)
"""

content += new_endpoint

with open('C:/Users/ACER/Documents/GitHub/SoftwareHorasMonitores/apps/work_sessions/api/views.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Endpoint created!')
