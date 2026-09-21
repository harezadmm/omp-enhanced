<?php
/**
 * Creates a published page containing an Elementor Pro form widget with a
 * File Upload field. Run inside the lab container after wp-load.php is loaded:
 *
 *   docker compose exec wordpress php -r 'require "wp-load.php"; include "/tmp/setup_form_page.php";'
 */

$post_id = wp_insert_post([
    'post_title'  => 'Upload Form',
    'post_name'   => 'upload-form',
    'post_status' => 'publish',
    'post_type'   => 'page',
]);
echo "page_id=$post_id\n";

$elementor_data = '[
  {
    "id": "a1b2c3d",
    "elType": "section",
    "settings": [],
    "elements": [
      {
        "id": "e5f6g7h",
        "elType": "column",
        "settings": { "_column_size": 100, "_inline_size": null },
        "elements": [
          {
            "id": "i9j0k1l",
            "elType": "widget",
            "widgetType": "form",
            "settings": {
              "form_name": "pocform",
              "submit_actions": [ "email" ],
              "form_fields": [
                { "custom_id": "name",  "field_type": "text",   "field_label": "Name",  "required": "true",  "width": "100" },
                { "custom_id": "email", "field_type": "email",  "field_label": "Email", "required": "true",  "width": "100" },
                { "custom_id": "dosya", "field_type": "upload", "field_label": "File",  "required": "",      "width": "100", "max_files": "5" }
              ],
              "button_text": "Send"
            },
            "elements": []
          }
        ]
      }
    ]
  }
]';

update_post_meta($post_id, '_elementor_data', $elementor_data);
update_post_meta($post_id, '_elementor_edit_mode', 'builder');
update_post_meta($post_id, '_wp_page_template', 'elementor_header_footer');
delete_post_meta($post_id, '_elementor_css');

echo "Elementor form page created: " . home_url("/?page_id=$post_id") . "\n";
