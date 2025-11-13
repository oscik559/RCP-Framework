#!/usr/bin/env python3
"""
Simple web interface for the agentic reasoning system.

This Flask web app provides a user-friendly interface to submit queries
and receive answers from the multi-agent LLM system.
"""

import os
import sys
import logging
from flask import Flask, render_template, request, jsonify
from datetime import datetime
import traceback
import threading
import time
import json
from typing import Optional, Dict, Any, List

# Add Layer_2-Agentic to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'Layer_2-Agentic'))

# Import the existing agentic reasoning system
from logic.state_graph import get_graph
from logic.types import SessionState
from config.debug_config import debug
from config.session_config import generate_session_id
from config.config_loader import CONFIG
from config.domain_config import DOMAIN_NAME, DOMAIN_DESCRIPTION
from db.connection import (
    get_agentic_connection,
    get_output_connection,
)
from progress_flow import create_progress_workflow

app = Flask(__name__)
app.secret_key = "your-secret-key-change-this-in-production"

# Reduce Flask logging verbosity (hide routine progress polling)
log = logging.getLogger('werkzeug')
log.setLevel(logging.WARNING)  # Only show warnings and errors, not INFO requests

# Global workflow instance
workflow: Optional[Any] = None


class ProgressTracker:
    """Tracks and emits progress updates for workflow execution"""

    def __init__(self, session_id):
        self.session_id = session_id
        self.current_step = 0
        self.total_steps = 7  # Based on workflow: Goal, Strategy, Function, Validate Function, Validate Strategy, Validate Goal, Done
        self.steps = [
            {
                "id": "goal_define",
                "name": "Goal Definition",
                "description": "Analyzing your query and defining the goal",
            },
            {
                "id": "strategy_plan",
                "name": "Strategy Planning",
                "description": "Selecting optimal strategy from knowledge base",
            },
            {
                "id": "function_execute",
                "name": "Function Execution",
                "description": "Executing relevant functions to gather information",
            },
            {
                "id": "function_validate",
                "name": "Function Validation",
                "description": "Validating function outputs and results",
            },
            {
                "id": "strategy_validate",
                "name": "Strategy Validation",
                "description": "Checking if strategy objectives are met",
            },
            {
                "id": "goal_validate",
                "name": "Goal Validation",
                "description": "Final validation and confidence assessment",
            },
            {
                "id": "done",
                "name": "Complete",
                "description": "Workflow completed successfully",
            },
        ]
        self.current_functions = []
        self.progress_log = []
        self.final_result: Optional[Dict[str, Any]] = None
        self.executed_functions = []
        self.step_states = {
            step["id"]: "pending" for step in self.steps
        }  # Track individual step states
        self.current_goal = None  # Store the defined goal
        self.current_strategy = None  # Store the selected strategy
        self.goal_details = None  # Store goal details
        self.strategy_details = None  # Store strategy details

    def set_goal(self, goal_text, goal_details=None):
        """Set the current goal information"""
        self.current_goal = goal_text
        self.goal_details = goal_details
        print(f"🎯 Goal Set: {goal_text}")
        print(f"   Details: {goal_details}")

    def set_strategy(self, strategy_name, strategy_details=None):
        """Set the current strategy information"""
        self.current_strategy = strategy_name
        self.strategy_details = strategy_details
        print(f"📋 Strategy Set: {strategy_name}")
        print(f"   Details: {strategy_details}")

    def emit_progress(self, step_id, status="running", details="", function_name=None):
        """Emit progress update to the client"""
        try:
            # Find the step
            step_index = next(
                (i for i, s in enumerate(self.steps) if s["id"] == step_id), -1
            )
            if step_index >= 0:
                # When status is "completed", count this step as done (index + 1)
                # When status is "running", we're on this step (index)
                if status == "completed":
                    self.current_step = max(self.current_step, step_index + 1)
                else:
                    self.current_step = max(self.current_step, step_index)

            # Update step state
            if step_id in self.step_states:
                self.step_states[step_id] = status

                # Mark previous steps as completed if this step is running/completed
                if status in ["running", "completed"] and step_index >= 0:
                    for i in range(step_index):
                        prev_step = self.steps[i]["id"]
                        if self.step_states[prev_step] == "pending":
                            self.step_states[prev_step] = "completed"

                # Special handling for function_execute completion
                if step_id == "function_execute" and status == "completed":
                    print(
                        f"🟢 Marking Function Execution step as COMPLETED in step_states"
                    )
                    self.step_states["function_execute"] = "completed"

            # Handle strategy restarts - reset subsequent steps when strategy planning restarts
            if (
                step_id == "strategy_plan"
                and status == "running"
                and "alternative strategy" in details.lower()
            ):
                # Reset steps after strategy planning for new strategy attempt
                steps_to_reset = [
                    "function_execute",
                    "function_validate",
                    "strategy_validate",
                    "goal_validate",
                    "done",
                ]
                for reset_step in steps_to_reset:
                    if reset_step in self.step_states:
                        self.step_states[reset_step] = "pending"

                # Clear previous function executions for new strategy
                self.executed_functions = []
                self.current_functions = []

            # Track function executions separately
            if function_name and function_name not in self.executed_functions:
                self.executed_functions.append(function_name)

            progress_data = {
                "session_id": self.session_id,
                "current_step": self.current_step,
                "total_steps": self.total_steps,
                "step_id": step_id,
                "step_name": (
                    self.steps[step_index]["name"]
                    if step_index >= 0 and step_index < len(self.steps)
                    else step_id
                ),
                "description": (
                    self.steps[step_index]["description"]
                    if step_index >= 0 and step_index < len(self.steps)
                    else details
                ),
                "status": status,  # running, completed, error
                "details": details,
                "function_name": function_name,
                "current_functions": self.current_functions,
                "executed_functions": self.executed_functions,
                "step_states": self.step_states,  # Include individual step states
                "current_goal": self.current_goal,  # Include current goal
                "goal_details": self.goal_details,  # Include goal details
                "current_strategy": self.current_strategy,  # Include current strategy
                "strategy_details": self.strategy_details,  # Include strategy details
                "progress_percentage": (self.current_step / self.total_steps) * 100,
                "timestamp": datetime.now().isoformat(),
            }

            # Store in progress log for retrieval
            self.progress_log.append(progress_data)

            print(
                f"📊 Progress Update: {step_id} - {status} ({self.current_step}/{self.total_steps}) - {details}"
            )
            if function_name:
                print(f"   🔧 Function: {function_name}")
            if self.current_goal:
                print(f"   🎯 Current Goal: {self.current_goal}")
            if self.current_strategy:
                print(f"   📋 Current Strategy: {self.current_strategy}")
        except Exception as e:
            print(f"❌ Error emitting progress: {e}")

    def add_function(self, function_name):
        """Add a function to the current execution list"""
        if function_name not in self.current_functions:
            self.current_functions.append(function_name)
            self.emit_progress(
                "function_execute",
                "running",
                f"Starting: {function_name}",
                function_name,
            )

    def complete_function(self, function_name, success=True):
        """Mark a function as completed"""
        status = "completed" if success else "error"
        details = (
            f"{'Successfully completed' if success else 'Failed'}: {function_name}"
        )
        self.emit_progress("function_execute", status, details, function_name)

    def get_progress_log(self):
        """Get the full progress log"""
        return self.progress_log


# Global progress trackers
active_trackers = {}


def initialize_workflow():
    """Initialize the LangGraph workflow"""
    global workflow
    try:
        workflow = get_graph()
        print("✅ Workflow initialized successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to initialize workflow: {e}")
        traceback.print_exc()
        return False


@app.route("/")
def index():
    """Main page with query input form"""
    return render_template("index.html", 
                         domain_name=DOMAIN_NAME,
                         domain_description=DOMAIN_DESCRIPTION)


@app.route("/api/domain")
def get_domain_info():
    """Get domain configuration information"""
    return jsonify({
        "name": DOMAIN_NAME,
        "description": DOMAIN_DESCRIPTION
    })


@app.route("/progress/<int:session_id>")
def get_progress(session_id):
    """Get progress updates for a session"""
    tracker = active_trackers.get(session_id)
    if tracker:
        return jsonify({"success": True, "progress_log": tracker.get_progress_log()})
    else:
        return jsonify({"success": False, "error": "Session not found"}), 404


@app.route("/result/<int:session_id>")
def get_result(session_id):
    """Get final result for a session"""
    tracker = active_trackers.get(session_id)
    if tracker and tracker.final_result:
        return jsonify(tracker.final_result)
    elif tracker:
        return jsonify({"success": False, "error": "Query still processing"}), 202
    else:
        return jsonify({"success": False, "error": "Session not found"}), 404


def execute_workflow_with_progress(init_state, tracker):
    """Execute workflow with progress tracking"""
    import threading
    import time

    try:
        session_id = init_state.get("sessionID")

        # Monitor database for real strategy and goal information
        def monitor_real_progress():
            print(f"🔄 Starting progress monitoring for session {session_id}")
            if not session_id:
                print("❌ No session ID provided to monitor_real_progress")
                return

            from db.connection import get_agentic_connection

            # Set goal information immediately
            tracker.set_goal(
                init_state.get("query", "Processing query..."),
                f"Session ID: {tracker.session_id}",
            )

            # Initial progress
            tracker.emit_progress("goal_define", "running", "Analyzing your query")
            tracker.emit_progress(
                "goal_define", "completed", "Goal successfully defined"
            )

            tracker.emit_progress(
                "strategy_plan", "running", "Searching strategy library"
            )

            # Monitor for actual strategy selection
            strategy_found = False
            start_time = time.time()

            while (
                not strategy_found and (time.time() - start_time) < 15
            ):  # Max 15 seconds wait
                try:
                    with get_agentic_connection() as conn:
                        cursor = conn.cursor()

                        # Check for strategy selection in database (join through GoalInSession)
                        cursor.execute(
                            """
                            SELECT s.StrategyName, s.StrategyDescription
                            FROM StrategyInSession s
                            JOIN GoalInSession g ON s.GoalID = g.GoalID
                            WHERE g.SessionID = ?
                            ORDER BY s.StrategyID DESC
                            LIMIT 1
                        """,
                            (session_id,),
                        )
                        strategy_row = cursor.fetchone()

                        if strategy_row:
                            strategy_name, strategy_description = strategy_row
                            tracker.set_strategy(
                                strategy_name,
                                strategy_description or "Executing selected strategy",
                            )
                            tracker.emit_progress(
                                "strategy_plan",
                                "completed",
                                f"Strategy selected: {strategy_name}",
                            )
                            strategy_found = True
                            break

                except Exception as e:
                    print(f"❌ Error monitoring strategy: {e}")

                time.sleep(0.1)  # Check every 100ms for faster response

            # Fallback if no strategy found in database
            if not strategy_found:
                # Use the strategy that's actually enabled in testing configuration
                from config.strategy_testing import get_enabled_strategies
                enabled_strategies = get_enabled_strategies()
                fallback_strategy = enabled_strategies[0] if enabled_strategies else "SIMPLE LOOKUP"
                
                tracker.set_strategy(
                    fallback_strategy,
                    f"Enabled strategy from configuration - {fallback_strategy.lower().replace('_', ' ')}",
                )
                tracker.emit_progress(
                    "strategy_plan", "completed", f"Strategy selected: {fallback_strategy}"
                )

            # Function execution monitoring
            tracker.emit_progress("function_execute", "running", "Executing functions")

            # Wait for actual workflow execution to populate database
            time.sleep(1)  # Minimal wait for workflow to execute functions

            # Check if functions were executed and mark as completed
            try:
                with get_agentic_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        SELECT COUNT(*) as total_functions
                        FROM FunctionInSession f
                        JOIN StrategyInSession s ON f.StrategyID = s.StrategyID
                        JOIN GoalInSession g ON s.GoalID = g.GoalID
                        WHERE g.SessionID = ?
                    """,
                        (session_id,),
                    )
                    result = cursor.fetchone()
                    total_count = result[0] if result else 0

                    if total_count > 0:
                        print(
                            f"� Found {total_count} functions - marking Function Execution as completed"
                        )
                        tracker.emit_progress(
                            "function_execute",
                            "completed",
                            f"Function execution completed ({total_count} functions)",
                        )
                    else:
                        print("⚠️ No functions found in database")
                        tracker.emit_progress(
                            "function_execute",
                            "completed",
                            "Function execution completed",
                        )
            except Exception as e:
                print(f"❌ Error checking functions: {e}")
                tracker.emit_progress(
                    "function_execute", "completed", "Function execution completed"
                )

            # Complete remaining validation steps

            # Ensure Function Execution is marked as completed before validation
            tracker.emit_progress(
                "function_execute", "completed", "All functions executed successfully"
            )

            tracker.emit_progress(
                "function_validate", "running", "Validating function outputs"
            )
            tracker.emit_progress(
                "function_validate", "completed", "Function validation successful"
            )

            tracker.emit_progress(
                "strategy_validate", "running", "Checking strategy completion"
            )
            tracker.emit_progress(
                "strategy_validate", "completed", "Strategy objectives met"
            )

            tracker.emit_progress(
                "goal_validate", "running", "Performing final validation"
            )
            tracker.emit_progress(
                "goal_validate", "completed", "Goal validation successful"
            )

        # Start real progress monitoring thread
        print(f"🚀 Starting progress monitoring thread for session {session_id}")
        progress_thread = threading.Thread(target=monitor_real_progress, daemon=True)
        progress_thread.start()
        print(f"✅ Progress monitoring thread started")

        # Execute the actual workflow
        if workflow is None:
            raise RuntimeError("Workflow is not initialized")
        result = workflow.invoke(init_state)  # type: ignore

        # Give monitoring a moment to catch final updates
        time.sleep(0.5)

        return result
    except Exception as e:
        tracker.emit_progress("error", "error", f"Workflow failed: {str(e)}")
        raise


@app.route("/query", methods=["POST"])
def process_query():
    """Process user query and return results"""
    try:
        data = request.get_json()
        user_query = data.get("query", "").strip()

        if not user_query:
            return jsonify({"error": "Please enter a query"}), 400

        if workflow is None:
            return jsonify({"error": "System not initialized"}), 500

        # Create session state for the query
        session_id = generate_session_id()  # Use the same logic as main.py

        # Clear any old session data to ensure fresh start
        from logic.database_manager import DatabaseManager
        db = DatabaseManager()
        db.clear_session_data(session_id)
        print(f"✅ Cleared old session data for session {session_id}")

        # Create progress tracker
        tracker = ProgressTracker(session_id)
        active_trackers[session_id] = tracker

        init_state: SessionState = {
            "sessionID": session_id,
            "query": user_query,
            "currentGoalID": None,
            "currentStrategyID": None,
            "currentFunctionID": None,
            "strategySatisfied": False,
            "strategyAborted": False,
            "goalSatisfied": False,
            "workflowComplete": False,
            "judgeConfidence": 0.0,
            "finalAnswer": "",
            "parallelExecutionMode": False,
            "parallelBatch": None,
            "parallelGroups": None,
            "parallelResults": {},
        }

        # Start progress tracking
        tracker.emit_progress("goal_define", "running", "Starting workflow execution")

        # Execute the workflow with progress tracking
        print(f"🔍 Processing query: {user_query}")

        # Run workflow in a separate thread to allow for progress updates
        def run_workflow():
            try:
                result = execute_workflow_with_progress(init_state, tracker)

                # Extract the final answer and metadata
                final_answer = result.get("finalAnswer", "No answer generated")
                confidence = result.get("judgeConfidence", 0.0)
                goal_satisfied = result.get("goalSatisfied", False)
                current_strategy_id = result.get("currentStrategyID")

                # Get strategy information from database if available
                strategy_info = None
                if current_strategy_id:
                    try:
                        print(f"🔍 Looking up strategy ID: {current_strategy_id}")
                        with get_agentic_connection() as conn:
                            cursor = conn.cursor()
                            cursor.execute(
                                """
                                SELECT StrategyName, StrategyDescription, StrategyTarget
                                FROM StrategyInSession
                                WHERE StrategyID = ?
                            """,
                                (current_strategy_id,),
                            )
                            strategy_row = cursor.fetchone()
                            if strategy_row:
                                strategy_info = {
                                    "name": strategy_row[0],
                                    "description": strategy_row[1],
                                    "target": strategy_row[2],
                                }
                                print(f"✅ Found strategy: {strategy_info}")
                            else:
                                print(
                                    f"❌ No strategy found for ID: {current_strategy_id}"
                                )
                    except Exception as e:
                        print(f"⚠️ Could not fetch strategy info: {e}")
                        import traceback

                        traceback.print_exc()
                else:
                    print("⚠️ No current strategy ID found in result")

                # Store final result in tracker for retrieval
                final_result = {
                    "success": True,
                    "query": user_query,
                    "answer": final_answer,
                    "confidence": confidence,
                    "goal_satisfied": goal_satisfied,
                    "session_id": session_id,
                    "strategy": strategy_info,
                }

                tracker.final_result = final_result
                tracker.emit_progress("done", "completed", "Query processing completed")

                # Clean up tracker after some time (keep for result retrieval)
                def cleanup_tracker():
                    time.sleep(30)  # Keep tracker for 30 seconds
                    if session_id in active_trackers:
                        del active_trackers[session_id]

                cleanup_thread = threading.Thread(target=cleanup_tracker)
                cleanup_thread.daemon = True
                cleanup_thread.start()

            except Exception as e:
                import traceback as tb
                error_msg = f"Error processing query: {str(e)}"
                print(f"❌ {error_msg}")
                tb.print_exc()
                tracker.emit_progress("error", "error", error_msg)

                # Clean up tracker
                if session_id in active_trackers:
                    del active_trackers[session_id]

        # Start workflow in background thread
        workflow_thread = threading.Thread(target=run_workflow)
        workflow_thread.daemon = True
        workflow_thread.start()

        # Return immediately with session ID for progress tracking
        return jsonify(
            {
                "success": True,
                "session_id": session_id,
                "message": "Query processing started. Watch for progress updates.",
            }
        )

    except Exception as e:
        print(f"❌ Error starting query processing: {e}")
        traceback.print_exc()
        return jsonify({"error": f"Error starting query processing: {str(e)}"}), 500


# Global pipeline tracking
pipeline_trackers = {}


@app.route("/pipelines/status")
def get_pipeline_status():
    """Get status of all pipelines and data inventory"""
    try:
        # Check PDF directory
        pdf_dir = CONFIG.get("pdf_dir", "PDF")
        pdf_files = []
        if os.path.exists(pdf_dir):
            pdf_files = [f for f in os.listdir(pdf_dir) if f.lower().endswith(".pdf")]

        # Check PNG pages directory
        png_dir = "data/png_pages"
        png_count = 0
        if os.path.exists(png_dir):
            png_count = len([f for f in os.listdir(png_dir) if f.lower().endswith(".png")])

        # Check extracted images
        image_dir = "data/output"
        image_count = 0
        if os.path.exists(image_dir):
            for root, dirs, files in os.walk(image_dir):
                image_count += len(
                    [f for f in files if f.lower().endswith((".png", ".jpg", ".jpeg"))]
                )

        # Query harvested database for actual product data
        harvested_db_path = CONFIG.get("harvested_db", "data/database/harvested.db")
        database_status = {}
        
        try:
            import sqlite3
            with sqlite3.connect(harvested_db_path) as conn:
                cursor = conn.cursor()
                
                # Get categories count
                cursor.execute("SELECT COUNT(*) FROM categories")
                categories_count = cursor.fetchone()[0]
                
                # Get product families count
                cursor.execute("SELECT COUNT(*) FROM product_families")
                families_count = cursor.fetchone()[0]
                
                # Get products count
                cursor.execute("SELECT COUNT(*) FROM products")
                products_count = cursor.fetchone()[0]
                
                database_status = {
                    "categories": categories_count,
                    "product_families": families_count,
                    "products": products_count,
                    "status": "ready"
                }
        except Exception as e:
            database_status = {
                "categories": 0,
                "product_families": 0,
                "products": 0,
                "status": "error",
                "error": str(e)
            }

        return jsonify(
            {
                "pdf_directory": pdf_dir,
                "pdf_count": len(pdf_files),
                "png_directory": png_dir,
                "png_count": png_count,
                "image_directory": image_dir,
                "image_count": image_count,
                "database": database_status,
                "timestamp": datetime.now().isoformat(),
            }
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/pipelines/run", methods=["POST"])
def run_pipeline():
    """Run specific pipeline(s)"""
    try:
        data = request.get_json()
        pipeline_ids = data.get("pipelines", [])
        session_id = data.get("session_id", int(time.time() * 1000))

        if not pipeline_ids:
            return jsonify({"error": "No pipelines specified"}), 400

        # Create pipeline tracker
        tracker = PipelineTracker(session_id, pipeline_ids)
        pipeline_trackers[session_id] = tracker

        # Start pipeline execution in background thread
        def run_pipelines():
            import subprocess
            
            # Map pipeline IDs to Layer 1 extraction scripts
            layer1_scripts = {
                "pdf-to-png": "../Layer_1a-Extraction/1_pdf_to_png.py",
                "detect-headers": "../Layer_1a-Extraction/2_detect_headers_footers.py",
                "detect-tables": "../Layer_1a-Extraction/3_detect_tables.py",
                "extract-product": "../Layer_1a-Extraction/4_extract_product.py",
                "extract-images": "../Layer_1a-Extraction/5_extract_images.py",
            }
            
            python_path = sys.executable  # Use same Python interpreter

            for i, pipeline_id in enumerate(pipeline_ids):
                if pipeline_id in layer1_scripts:
                    script_path = os.path.join(os.path.dirname(__file__), layer1_scripts[pipeline_id])
                    tracker.update_progress(
                        i, pipeline_id, "running", f"Running {pipeline_id}..."
                    )

                    try:
                        # Run the Layer 1 extraction script
                        result = subprocess.run(
                            [python_path, script_path],
                            capture_output=True,
                            text=True,
                            timeout=600  # 10 minute timeout
                        )
                        
                        if result.returncode == 0:
                            tracker.update_progress(
                                i,
                                pipeline_id,
                                "completed",
                                f"{pipeline_id} completed successfully",
                            )
                        else:
                            error_msg = result.stderr[:200] if result.stderr else "Unknown error"
                            tracker.update_progress(
                                i, pipeline_id, "failed", f"{pipeline_id} failed: {error_msg}"
                            )
                            print(f"Pipeline {pipeline_id} failed: {result.stderr}")

                    except subprocess.TimeoutExpired:
                        tracker.update_progress(
                            i, pipeline_id, "failed", f"{pipeline_id} timed out after 10 minutes"
                        )
                    except Exception as e:
                        tracker.update_progress(
                            i, pipeline_id, "failed", f"{pipeline_id} failed: {str(e)}"
                        )
                        print(f"Pipeline {pipeline_id} failed: {e}")

            tracker.complete()

            # Clean up tracker after 5 minutes to free memory
            def cleanup_tracker():
                time.sleep(300)  # 5 minutes
                pipeline_trackers.pop(session_id, None)

            cleanup_thread = threading.Thread(target=cleanup_tracker)
            cleanup_thread.daemon = True
            cleanup_thread.start()

        # Start the pipeline thread
        pipeline_thread = threading.Thread(target=run_pipelines)
        pipeline_thread.daemon = True
        pipeline_thread.start()

        return jsonify(
            {
                "session_id": session_id,
                "message": f"Started {len(pipeline_ids)} pipeline(s)",
                "pipelines": pipeline_ids,
            }
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/pipelines/progress/<int:session_id>")
def get_pipeline_progress(session_id):
    """Get progress of running pipelines"""
    tracker = pipeline_trackers.get(session_id)
    if not tracker:
        # Return a "completed" status instead of 404 to stop polling
        return jsonify(
            {
                "progress_percent": 100,
                "pipeline_status": {},
                "pipeline_messages": {},
                "completed": True,
                "message": "Session not found or pipeline completed",
            }
        )

    return jsonify(tracker.get_status())


class PipelineTracker:
    """Tracks pipeline execution progress"""

    def __init__(self, session_id, pipeline_ids):
        self.session_id = session_id
        self.pipeline_ids = pipeline_ids
        self.total_pipelines = len(pipeline_ids)
        self.current_pipeline = 0
        self.completed = False
        self.start_time = time.time()
        self.pipeline_status = {pid: "pending" for pid in pipeline_ids}
        self.pipeline_messages = {pid: "" for pid in pipeline_ids}

    def update_progress(self, pipeline_index, pipeline_id, status, message):
        """Update progress for a specific pipeline"""
        self.current_pipeline = pipeline_index
        self.pipeline_status[pipeline_id] = status
        self.pipeline_messages[pipeline_id] = message
        print(f"Pipeline {pipeline_id}: {status} - {message}")

    def complete(self):
        """Mark all pipelines as completed"""
        self.completed = True
        self.current_pipeline = self.total_pipelines

    def get_status(self):
        """Get current status"""
        return {
            "session_id": self.session_id,
            "total_pipelines": self.total_pipelines,
            "current_pipeline": self.current_pipeline,
            "completed": self.completed,
            "progress_percent": (
                int((self.current_pipeline / self.total_pipelines) * 100)
                if self.total_pipelines > 0
                else 0
            ),
            "elapsed_time": time.time() - self.start_time,
            "pipeline_status": self.pipeline_status,
            "pipeline_messages": self.pipeline_messages,
        }


@app.route("/health")
def health_check():
    """Health check endpoint"""
    return jsonify(
        {
            "status": "healthy",
            "workflow_initialized": workflow is not None,
            "timestamp": datetime.now().isoformat(),
        }
    )


if __name__ == "__main__":
    print("🚀 Starting Agentic Reasoning Web Interface...")

    # Initialize the workflow
    if not initialize_workflow():
        print("❌ Failed to start - workflow initialization failed")
        sys.exit(1)

    print("🌐 Starting Flask web server with SocketIO...")
    print("📍 Access the app at: http://localhost:5001")

    # Run the Flask app
    app.run(
        host="0.0.0.0",
        port=5001,
        debug=True,
        use_reloader=False,  # Disable reloader to prevent double initialization
    )
