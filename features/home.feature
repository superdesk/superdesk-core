Feature: Home API 

    Scenario: Fetch resources list
        When we get "/"
        Then we get response code 200
        """
        {
            "_links": {
                "child": [
                {
                    "href": "sessions",
                    "title": "sessions"
                },
                {
                    "href": "users/<user>/sessions",
                    "title": "clear_sessions"
                },
                {
                    "href": "auth",
                    "title": "auth"
                },
                {
                    "href": "roles",
                    "title": "roles"
                },
                {
                    "href": "allowed_values",
                    "title": "allowed_values"
                },
                {
                    "href": "picture_crop",
                    "title": "picture_crop"
                },
                {
                    "href": "picture_renditions",
                    "title": "picture_renditions"
                },
                {
                    "href": "video_edit",
                    "title": "video_edit"
                },
                {
                    "href": "content_api",
                    "title": "content_api"
                },
                {
                    "href": "items",
                    "title": "items"
                },
                {
                    "href": "capi_items_internal",
                    "title": "capi_items_internal"
                },
                {
                    "href": "search_capi",
                    "title": "search_capi"
                },
                {
                    "href": "backend_meta",
                    "title": "backend_meta"
                },
                {
                    "href": "config",
                    "title": "config"
                },
                {
                    "href": "internal_destinations",
                    "title": "internal_destinations"
                },
                {
                    "href": "client_config",
                    "title": "client_config"
                },
                {
                    "href": "attachments",
                    "title": "attachments"
                },
                {
                    "href": "auth_server_clients",
                    "title": "auth_server_clients"
                },
                {
                    "href": "links",
                    "title": "links"
                },
                {
                    "href": "usage-metrics",
                    "title": "usage-metrics"
                },
                {
                    "href": "languages",
                    "title": "languages"
                },
                {
                    "href": "users",
                    "title": "users"
                },
                {
                    "href": "user_metrics",
                    "title": "user_metrics"
                },
                {
                    "href": "auth_db",
                    "title": "auth_db"
                },
                {
                    "href": "reset_user_password",
                    "title": "reset_user_password"
                },
                {
                    "href": "change_user_password",
                    "title": "change_user_password"
                },
                {
                    "href": "auth_xmpp",
                    "title": "auth_xmpp"
                },
                {
                    "href": "upload",
                    "title": "upload"
                },
                {
                    "href": "download",
                    "title": "download"
                },
                {
                    "href": "activity",
                    "title": "activity"
                },
                {
                    "href": "audit",
                    "title": "audit"
                },
                {
                    "href": "vocabularies",
                    "title": "vocabularies"
                },
                {
                    "href": "comments",
                    "title": "comments"
                },
                {
                    "href": "ingest_providers",
                    "title": "ingest_providers"
                },
                {
                    "href": "io_errors",
                    "title": "io_errors"
                },
                {
                    "href": "ingest",
                    "title": "ingest"
                },
                {
                    "href": "feed_parsers_allowed",
                    "title": "feed_parsers_allowed"
                },
                {
                    "href": "feeding_services_allowed",
                    "title": "feeding_services_allowed"
                },
                {
                    "href": "webhook",
                    "title": "webhook"
                },
                {
                    "href": "spellcheckers_list",
                    "title": "spellcheckers_list"
                },
                {
                    "href": "spellchecker",
                    "title": "spellchecker"
                },
                {
                    "href": "ai",
                    "title": "ai"
                },
                {
                    "href": "ai_data_op",
                    "title": "ai_data_op"
                },
                {
                    "href": "ai_image_suggestions",
                    "title": "ai_image_suggestions"
                },
                {
                    "href": "restore_record",
                    "title": "restore_record"
                },
                {
                    "href": "media_references",
                    "title": "media_references"
                },
                {
                    "href": "media_editor",
                    "title": "media_editor"
                },
                {
                    "href": "archive",
                    "title": "archive"
                },
                {
                    "href": "archive/<item_id>/lock",
                    "title": "archive_lock"
                },
                {
                    "href": "archive/<item_id>/unlock",
                    "title": "archive_unlock"
                },
                {
                    "href": "archive/spike",
                    "title": "archive_spike"
                },
                {
                    "href": "archive/unspike",
                    "title": "archive_unspike"
                },
                {
                    "href": "users/<original_creator>/content",
                    "title": "user_content"
                },
                {
                    "href": "archive/<original_id>/rewrite",
                    "title": "archive_rewrite"
                },
                {
                    "href": "archive/correction",
                    "title": "archive_correction"
                },
                {
                    "href": "archive_autosave",
                    "title": "archive_autosave"
                },
                {
                    "href": "archive/<item_id>/related",
                    "title": "archive_related"
                },
                {
                    "href": "news",
                    "title": "news"
                },
                {
                    "href": "item_comments",
                    "title": "item_comments"
                },
                {
                    "href": "archive/<item>/comments",
                    "title": "archive/<path:item>/comments"
                },
                {
                    "href": "archive_autocomplete",
                    "title": "archive_autocomplete"
                },
                {
                    "href": "archive_history",
                    "title": "archive_history"
                },
                {
                    "href": "stages",
                    "title": "stages"
                },
                {
                    "href": "stages_order",
                    "title": "stages_order"
                },
                {
                    "href": "desks",
                    "title": "desks"
                },
                {
                    "href": "users/<user_id>/desks",
                    "title": "user_desks"
                },
                {
                    "href": "desks/<desk_id>/sluglines",
                    "title": "desks/<regex(\"[a-f0-9]{24}\"):desk_id>/sluglines"
                },
                {
                    "href": "desks/<agg_type>",
                    "title": "desk_overview"
                },
                {
                    "href": "desks/<desk_id>/users",
                    "title": "desk_users"
                },
                {
                    "href": "tasks",
                    "title": "tasks"
                },
                {
                    "href": "preferences",
                    "title": "preferences"
                },
                {
                    "href": "spikes",
                    "title": "spikes"
                },
                {
                    "href": "prepopulate",
                    "title": "prepopulate"
                },
                {
                    "href": "legal_archive",
                    "title": "legal_archive"
                },
                {
                    "href": "legal_archive_history",
                    "title": "legal_archive_history"
                },
                {
                    "href": "legal_publish_queue",
                    "title": "legal_publish_queue"
                },
                {
                    "href": "search",
                    "title": "search"
                },
                {
                    "href": "saved_searches",
                    "title": "saved_searches"
                },
                {
                    "href": "all_saved_searches",
                    "title": "all_saved_searches"
                },
                {
                    "href": "saved_searches/<saved_search_id>/items",
                    "title": "saved_search_items"
                },
                {
                    "href": "suggestions/<item_id>",
                    "title": "suggestions/<regex(\"[\\w,.:_-]+\"):item_id>"
                },
                {
                    "href": "privileges",
                    "title": "privileges"
                },
                {
                    "href": "rule_sets",
                    "title": "rule_sets"
                },
                {
                    "href": "routing_schemes",
                    "title": "routing_schemes"
                },
                {
                    "href": "ingest_rule_handlers",
                    "title": "ingest_rule_handlers"
                },
                {
                    "href": "highlights",
                    "title": "highlights"
                },
                {
                    "href": "marked_for_highlights",
                    "title": "marked_for_highlights"
                },
                {
                    "href": "generate_highlights",
                    "title": "generate_highlights"
                },
                {
                    "href": "marked_for_desks",
                    "title": "marked_for_desks"
                },
                {
                    "href": "archive/publish",
                    "title": "archive_publish"
                },
                {
                    "href": "archive/kill",
                    "title": "archive_kill"
                },
                {
                    "href": "archive/correct",
                    "title": "archive_correct"
                },
                {
                    "href": "archive/takedown",
                    "title": "archive_takedown"
                },
                {
                    "href": "published",
                    "title": "published"
                },
                {
                    "href": "archive/<original_id>/resend",
                    "title": "archive_resend"
                },
                {
                    "href": "published_package_items",
                    "title": "published_package_items"
                },
                {
                    "href": "archive/unpublish",
                    "title": "archive_unpublish"
                },
                {
                    "href": "export",
                    "title": "export"
                },
                {
                    "href": "formatters",
                    "title": "formatters"
                },
                {
                    "href": "output_formats",
                    "title": "output_formats"
                },
                {
                    "href": "content_types",
                    "title": "content_types"
                },
                {
                    "href": "dictionaries",
                    "title": "dictionaries"
                },
                {
                    "href": "ingest/<id>/fetch",
                    "title": "fetch"
                },
                {
                    "href": "archive/<guid>/duplicate",
                    "title": "duplicate"
                },
                {
                    "href": "archive/translate",
                    "title": "translate"
                },
                {
                    "href": "archive/<guid>/copy",
                    "title": "copy"
                },
                {
                    "href": "archive/<guid>/move",
                    "title": "move"
                },
                {
                    "href": "spellcheck",
                    "title": "spellcheck"
                },
                {
                    "href": "content_templates",
                    "title": "content_templates"
                },
                {
                    "href": "content_templates_apply",
                    "title": "content_templates_apply"
                },
                {
                    "href": "archived",
                    "title": "archived"
                },
                {
                    "href": "validators",
                    "title": "validators"
                },
                {
                    "href": "validate",
                    "title": "validate"
                },
                {
                    "href": "workspaces",
                    "title": "workspaces"
                },
                {
                    "href": "macros",
                    "title": "macros"
                },
                {
                    "href": "archive/<item_id>/broadcast",
                    "title": "archive_broadcast"
                },
                {
                    "href": "search_providers",
                    "title": "search_providers"
                },
                {
                    "href": "search_providers_proxy",
                    "title": "search_providers_proxy"
                },
                {
                    "href": "search_providers_allowed",
                    "title": "search_providers_allowed"
                },
                {
                    "href": "workqueue",
                    "title": "workqueue"
                },
                {
                    "href": "contacts",
                    "title": "contacts"
                },
                {
                    "href": "contacts/organisations",
                    "title": "contacts_organisations"
                },
                {
                    "href": "concept_items",
                    "title": "concept_items"
                },
                {
                    "href": "places_autocomplete",
                    "title": "places_autocomplete"
                },
                {
                    "href": "closed_desks",
                    "title": "closed_desks"
                },
                {
                    "href": "system_messages",
                    "title": "system_messages"
                },
                {
                    "href": "user_availability",
                    "title": "user_availability"
                },
                {
                    "href": "default_user_availability",
                    "title": "default_user_availability"
                },
                {
                    "href": "agenda",
                    "title": "agenda"
                },
                {
                    "href": "planning_export_templates",
                    "title": "planning_export_templates"
                },
                {
                    "href": "planning_types",
                    "title": "planning_types"
                },
                {
                    "href": "locations",
                    "title": "locations"
                },
                {
                    "href": "events/<item_id>/lock",
                    "title": "events_lock"
                },
                {
                    "href": "events/<item_id>/unlock",
                    "title": "events_unlock"
                },
                {
                    "href": "events",
                    "title": "events"
                },
                {
                    "href": "events/post",
                    "title": "events_post"
                },
                {
                    "href": "events_files",
                    "title": "events_files"
                },
                {
                    "href": "events_template",
                    "title": "events_template"
                },
                {
                    "href": "recent_events_template",
                    "title": "recent_events_template"
                },
                {
                    "href": "planning",
                    "title": "planning"
                },
                {
                    "href": "planning/<item_id>/lock",
                    "title": "planning_lock"
                },
                {
                    "href": "planning/<item_id>/unlock",
                    "title": "planning_unlock"
                },
                {
                    "href": "planning/post",
                    "title": "planning_post"
                },
                {
                    "href": "planning_files",
                    "title": "planning_files"
                },
                {
                    "href": "planning/cancel",
                    "title": "planning_cancel"
                },
                {
                    "href": "planning_featured_lock",
                    "title": "planning_featured_lock"
                },
                {
                    "href": "planning_featured_unlock",
                    "title": "planning_featured_unlock"
                },
                {
                    "href": "assignments/<item_id>/lock",
                    "title": "assignments_lock"
                },
                {
                    "href": "assignments/<item_id>/unlock",
                    "title": "assignments_unlock"
                },
                {
                    "href": "assignments",
                    "title": "assignments"
                },
                {
                    "href": "assignments/content",
                    "title": "assignments_content"
                },
                {
                    "href": "assignments/link",
                    "title": "assignments_link"
                },
                {
                    "href": "assignments/unlink",
                    "title": "assignments_unlink"
                },
                {
                    "href": "assignments/complete",
                    "title": "assignments_complete"
                },
                {
                    "href": "assignments/revert",
                    "title": "assignments_revert"
                },
                {
                    "href": "planning_search",
                    "title": "planning_search"
                },
                {
                    "href": "events_planning_search",
                    "title": "events_planning_search"
                },
                {
                    "href": "planning_article_export",
                    "title": "planning_article_export"
                },
                {
                    "href": "published_planning",
                    "title": "published_planning"
                },
                {
                    "href": "shows",
                    "title": "shows"
                },
                {
                    "href": "rundowns",
                    "title": "rundowns"
                },
                {
                    "href": "rundown_items",
                    "title": "rundown_items"
                },
                {
                    "href": "/shows/<show>/templates",
                    "title": "rundown_templates"
                },
                {
                    "href": "rundown_export",
                    "title": "rundown_export"
                },
                {
                    "href": "rundown_comments",
                    "title": "rundown_comments"
                },
                {
                    "href": "content_filters",
                    "title": "content_filters"
                },
                {
                    "href": "filter_conditions",
                    "title": "filter_conditions"
                },
                {
                    "href": "products",
                    "title": "products"
                },
                {
                    "href": "publish_queue",
                    "title": "publish_queue"
                },
                {
                    "href": "subscribers",
                    "title": "subscribers"
                },
                {
                    "href": "subscriber_token",
                    "title": "subscriber_token"
                },
                {
                    "href": "filter_conditions/parameters",
                    "title": "filter_conditions/parameters"
                },
                {
                    "href": "content_filters/test",
                    "title": "content_filter_tests"
                },
                {
                    "href": "products/test",
                    "title": "product_tests"
                },
                {
                    "href": "events_history",
                    "title": "events_history"
                },
                {
                    "href": "planning_history",
                    "title": "planning_history"
                },
                {
                    "href": "event_autosave",
                    "title": "event_autosave"
                },
                {
                    "href": "planning_featured",
                    "title": "planning_featured"
                },
                {
                    "href": "planning_autosave",
                    "title": "planning_autosave"
                },
                {
                    "href": "events_planning_filters",
                    "title": "events_planning_filters"
                },
                {
                    "href": "assignments_history",
                    "title": "assignments_history"
                },
                {
                    "href": "planning_locks",
                    "title": "planning_locks"
                },
                {
                    "href": "planning/spike/<string:planning_id>",
                    "title": "planning_spike"
                },
                {
                    "href": "planning/unspike/<string:planning_id>",
                    "title": "planning_unspike"
                },
                {
                    "href": "planning/<string:planning_id>/duplicate",
                    "title": "planning_duplicate"
                },
                {
                    "href": "planning/postpone/<string:planning_id>",
                    "title": "planning_postpone"
                },
                {
                    "href": "events/update_time/<string:event_id>",
                    "title": "events_update_time"
                },
                {
                    "href": "events/spike/<string:event_id>",
                    "title": "events_spike"
                },
                {
                    "href": "events/unspike/<string:event_id>",
                    "title": "events_unspike"
                },
                {
                    "href": "events/postpone/<string:event_id>",
                    "title": "events_postpone"
                },
                {
                    "href": "events/cancel/<string:event_id>",
                    "title": "events_cancel"
                },
                {
                    "href": "events/reschedule/<string:event_id>",
                    "title": "events_reschedule"
                },
                {
                    "href": "events/update_repetitions/<string:event_id>",
                    "title": "events_update_repetitions"
                },
                {
                    "href": "/planning_download/events",
                    "title": "planning_download_file"
                },
                {
                    "href": "/apidocs",
                    "title": "content_api_docs"
                },
                {
                    "href": "/api-planning-static/<path:filename>",
                    "title": "api_planning_static_file"
                }
                ]
            }
        }
        """
