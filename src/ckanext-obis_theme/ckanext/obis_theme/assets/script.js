ckan.module("obis_theme-module", function ($, _) {
  "use strict";
  return {
    options: {
      debug: false,
    },

    initialize: function () {},
  };
});

$(document).ready(function() {
    // Facet collapse toggle
    $('[data-toggle="collapse"]').off('click').on('click', function(e) {
        e.preventDefault();
        var target = $(this).attr('href');
        $(target).collapse('toggle');
    });

    // Rotate caret based on collapse state
    $(document).on('show.bs.collapse', '.collapse', function() {
        var id = $(this).attr('id');
        $('[href="#' + id + '"] .facet-caret').css('transform', 'rotate(180deg)');
    });

    $(document).on('hide.bs.collapse', '.collapse', function() {
        var id = $(this).attr('id');
        $('[href="#' + id + '"] .facet-caret').css('transform', 'rotate(0deg)');
    });
});

// Custom user autocomplete for member_new pages.
// Shows "Full Name (username)" in the dropdown instead of just the username.
// Removes ignore_self so users can add themselves to orgs/groups.
ckan.module('obis-user-autocomplete', function ($) {
  return {
    initialize: function () {
      var el = this.el;

      el.select2({
        minimumInputLength: 2,
        ajax: {
          url: '/api/2/util/user/autocomplete',
          dataType: 'json',
          quietMillis: 200,
          data: function (term) {
            return { q: term };
          },
          results: function (data) {
            var items = $.map(data, function (user) {
              var label = user.fullname
                ? user.fullname + ' (' + user.name + ')'
                : user.name;
              return { id: user.name, text: label };
            });
            return { results: items };
          }
        },
        initSelection: function (element, callback) {
          var val = element.val();
          if (val) {
            callback({ id: val, text: val });
          }
        },
        placeholder: 'Search for a user...',
      });
    }
  };
});