{{/*
Base name for every object: "taskboard" for a release called taskboard, otherwise "<release>-taskboard".
Services, the Ingress, the HPA, the frontend proxy and the backend's DATABASE_URL all build their
names from this one helper, so they cannot drift apart.
*/}}
{{- define "taskboard.fullname" -}}
{{- if contains .Chart.Name .Release.Name -}}
{{ .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else -}}
{{ printf "%s-%s" .Release.Name .Chart.Name | trunc 63 | trimSuffix "-" }}
{{- end -}}
{{- end }}

{{- define "taskboard.backend" -}}{{ include "taskboard.fullname" . }}-backend{{- end }}
{{- define "taskboard.frontend" -}}{{ include "taskboard.fullname" . }}-frontend{{- end }}
{{- define "taskboard.postgres" -}}{{ include "taskboard.fullname" . }}-postgres{{- end }}
