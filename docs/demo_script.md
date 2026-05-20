# Demo Script

1. Open frontend: `http://localhost:5178`
2. Open gateway Swagger: `http://localhost:8580/docs`
3. Run demo ingestion workflow:
   - `python scripts/demo_pipeline.py`
4. Show service health:
   - `GET /services/health`
5. Open dashboard API for demo asset:
   - `GET /dashboard/AST-BRIDGE-001?actor_role=engineer`
6. Show report export:
   - `GET /reports/export/AST-BRIDGE-001?format=csv&actor_role=inspector`
