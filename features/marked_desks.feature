Feature: Marked For Desks

  @auth
  Scenario: Mark a story for a desk
        Given "desks"
        """
        [{"name": "desk1"}]
        """
        When we post to "archive"
        """
        [{"headline": "test"}]
        """
        When we post to "/marked_for_desks" with success
        """
        [{"marked_desk": "#desks._id#", "marked_item": "#archive._id#"}]
        """
        Then we get new resource
        """
        {"marked_desk": "#desks._id#", "marked_item": "#archive._id#"}
        """
        When we get "archive"
        Then we get list with 1 items
        """
        {"_items": [{"headline": "test", "marked_desks": [{"desk_id": "#desks._id#", "user_marked": "#user._id#"}]}]}
        """
        When we post to "marked_for_desks"
        """
        [{"marked_desk": "#desks._id#", "marked_item": "#archive._id#"}]
        """
        And we get "archive"
        Then we get list with 1 items
        """
        {"_items": [{"marked_desks": []}]}
        """