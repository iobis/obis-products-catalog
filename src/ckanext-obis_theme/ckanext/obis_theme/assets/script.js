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