function display_additional_information(data) {
    if(data) {
      data = data.replace(/(?:\r\n|\r|\n)/g, '<br>');
      return `<span 
        data-toggle="tooltip"
        data-html="true" 
        data-contrainer="body"
        title="${data}">
        <i class="fa fas fa-info-circle fa-2x centered-icon"></i>
      </span>`
    }

    return ""
}

function display_n_register(data, type, row) {
    // display registered persons with a progress bar
    let current = data;
    let n = row['n_places'];
    let element = '<span>' + current + '/' + n + '</span>' +
        '<div class="progress">' +
        '    <div' +
        '       class="progress-bar"' +
        '       role="progressbar"' +
        '       aria-valuenow="' + current + '"' +
        '       aria-valuemin="0"' +
        '       aria-valuemax="' + n + '"' +
        '       style="width: ' + Math.round(current/n * 100) + '%"' +
        '></div>' +
        '</div>';
    return element;
  }

function display_slot_speakers(data, type, row) {
    // data : array of objects {email, last_name, first_name}
    let element = '';
    let filter_txt = '';

    $.each(data, function(i, speaker) {
      element += `<a href="mailto:${speaker.email}">${speaker.last_name} ${speaker.first_name}</a><br>`
      filter_txt += `${speaker.last_name} ${speaker.first_name} `
    });

    if(type === 'filter') {
      return filter_txt.normalize("NFD").replace(/\p{Diacritic}/gu, "")
    }

    return element;
}

function display_slot_date(data, type, row) {
    // data : datetime serialized by django
    const date_options = {
      year: "numeric",
      month: "numeric",
      day: "numeric",
      weekday: "long",
    };
    let date = is_set(data) ? data : ''
    let start_time = is_set(row.start_time) ? row.start_time.slice(0, -3) : ''
    let end_time = is_set(row.end_time) ? row.end_time.slice(0, -3) : ''
    let txt = ""

    if(type === "display") {
      txt += date !== '' ? `<span>${formatDate(date, date_options)}</span>` : ''
      txt += txt !== '' ? '<br>' : ''
      txt += start_time !== '' ? `<span>${start_time} - ${end_time}</span>` : ''
      return txt;
    }
    else if(type === 'filter') {
      return `${formatDate(date, date_options)} ${start_time} ${end_time}`
    }

    return data;
}

function display_slot_restrictions(data, type, row) {
    let establishment_restrictions = ""
    let levels_restrictions = ""
    let span_txt = ""
    let bachelors_types = ""
    let bachelors_mentions = ""
    let bachelors_teachings = ""

    if(row.establishment_restrictions === true) {
      establishment_restrictions += `${establishments_txt} :<br>`
      row.allowed_establishments_list.forEach(item => {
        establishment_restrictions += `- ${item}<br>`
      })

      row.allowed_highschools_list.forEach(json => {
        establishment_restrictions += `- ${json['city']} - ${json['label']}<br>`
      })
    }

    if(row.levels_restrictions === true) {
      levels_restrictions += `${levels_txt} :<br>`

      row.allowed_highschool_levels_list.forEach(item => {
        levels_restrictions += `- ${item}<br>`
      })

      row.allowed_post_bachelor_levels_list.forEach(item => {
        levels_restrictions += `- ${item}<br>`
      })

      row.allowed_student_levels_list.forEach(item => {
        levels_restrictions += `- ${item}<br>`
      })
    }

    if(row.bachelors_restrictions === true) {
      if(row.allowed_bachelor_types_list.length > 0) {
        bachelors_types += `${bachelors_txt} : <br>`
        row.allowed_bachelor_types_list.forEach(item => {
          bachelors_types += `- ${item} <br>`
        })
      }

      if(row.allowed_bachelor_mentions_list.length > 0) {
        bachelors_mentions += `${allowed_mentions_txt} :<br>`
        row.allowed_bachelor_mentions_list.forEach(item => {
          bachelors_mentions += `- ${item} <br>`
        })
      }

      if(row.allowed_bachelor_teachings_list.length > 0) {
        bachelors_teachings += `${allowed_teachings_txt} :<br>`
        row.allowed_bachelor_teachings_list.forEach(item => {
          bachelors_teachings += `- ${item} <br>`
        })
      }
    }

    if (establishment_restrictions.length > 0) {
      span_txt += `<li data-toggle="tooltip" data-html="true" data-container="body" title="${establishment_restrictions}"><i class="fa fas fa-info-circle fa-fw"></i> ${establishments_txt}</li>`
    }

    if (levels_restrictions.length > 0) {
      span_txt += `<li data-toggle="tooltip" data-html="true" data-container="body" title="${levels_restrictions}"><i class="fa fas fa-info-circle fa-fw"></i> ${levels_txt}</li>`
    }

    if (bachelors_types.length > 0) {
      span_txt += `<li data-toggle="tooltip" data-html="true" data-container="body" title="${bachelors_types}"><i class="fa fas fa-info-circle fa-fw"></i> ${bachelors_txt}</li>`
    }

    if (bachelors_mentions.length > 0) {
      span_txt += `<li data-toggle="tooltip" data-html="true" data-container="body" title="${bachelors_mentions}"><i class="fa fas fa-info-circle fa-fw"></i> ${allowed_mentions_txt}</li>`
    }

    if (bachelors_teachings.length > 0) {
      span_txt += `<li data-toggle="tooltip" data-html="true" data-container="body" title="${bachelors_teachings}"><i class="fa fas fa-info-circle fa-fw"></i> ${allowed_teachings_txt}</li>`
    }

    return `<ul class="list-unstyled">${span_txt}<ul>`
}