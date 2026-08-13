import json

INPUT_FILE = "data/incidents.jsonl"
OUTPUT_FILE = "data/prepared.jsonl"


def incident_to_text(incident):
    anomaly = incident["anomaly"]
    metrics = incident["metrics"]
    root = incident["root_cause"]
    impact = incident["impact"]
    context = incident["context"]

    logs = " | ".join(
        log["message"]
        for log in incident["logs"]
    )

    recent_changes = " | ".join(
        context["recent_changes"]
    )

    return f"""
Incident type: {anomaly["type"]}
Severity: {anomaly["severity"]}

Problem:
{anomaly["description"]}

Detected metric:
{anomaly["detected_metric"]}

Expected value:
{anomaly["expected_value"]}

Actual value:
{anomaly["actual_value"]}

Operational evidence:
Records processed: {metrics["records_processed"]}
Records failed: {metrics["records_failed"]}
Error rate: {metrics["error_rate"]}
Expected error rate: {metrics["expected_error_rate"]}
Processing time: {metrics["processing_time_seconds"]} seconds
Expected processing time: {metrics["expected_processing_time_seconds"]} seconds

Logs:
{logs}

Recent changes:
{recent_changes}

Root cause:
Category: {root["category"]}
{root["description"]}

Impact:
Affected records: {impact["affected_records"]}
Affected services: {", ".join(impact["affected_services"])}
{impact["business_impact"]}
""".strip()


with open(INPUT_FILE, "r", encoding="utf-8") as infile, \
     open(OUTPUT_FILE, "w", encoding="utf-8") as outfile:

    count = 0

    for line in infile:
        incident = json.loads(line)

        document = {
            "incident_id": incident["incident_id"],
            "text": incident_to_text(incident)
        }

        outfile.write(
            json.dumps(document, ensure_ascii=False) + "\n"
        )

        count += 1

print(f"Prepared {count} incidents.")