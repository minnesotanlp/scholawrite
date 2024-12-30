$(document).ready(function() {
    $('#title').change(function() {
        console.log($(this).val())
        window.location.pathname = "/sankey/" + $(this).val()
        sessionStorage.setItem("proejct_id", $(this).val());
    });

    if (typeof graphJSON !== 'undefined'){
        (async function() {
            await Plotly.react('sankey-plot', graphJSON.data, graphJSON.layout);

            $('.sankey-link').on('mouseover', function() {
                $(this).css('fill-opacity', 0.8);
            }).on('mouseout', function() {
                $(this).css('fill-opacity', 0.4);
            });
        })();
    }

    $('#update').click(function() {
        var show_hidden_links = $('#show_hidden_links')[0].checked

        var hidden_labels = $('.labels:checked').map(function() {
            return parseInt(this.value);
        }).get();

        update_sankey(sessionStorage.getItem("proejct_id"), hidden_labels, show_hidden_links)
    });
});




function update_sankey(project_id, ignore_list, show_hidden_link){
    fetch('/update-sankey', {
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            },
            method: 'POST',
            body: JSON.stringify({project_id: project_id, ignore_list: ignore_list, show_hidden_link: show_hidden_link})
        })
        .then(response => response.json())
        .then(data => {
            var fig = JSON.parse(data);

            Plotly.react('sankey-plot', fig.data, fig.layout);
    });
}