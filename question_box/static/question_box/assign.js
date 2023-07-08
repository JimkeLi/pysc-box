document.addEventListener('DOMContentLoaded', function() {

    //When forms are submitted
    Array.from(document.querySelectorAll('form')).forEach(form => {
        form.onsubmit = () =>{
            let box_id = form.id.slice(4);

            //Get the id of the thera assigned to answer
            let answered_by_html_id = "answered_by" + box_id;
            let confirmed_by_html_id = "confirmed_by" + box_id;
            let answered_by = document.querySelector(`#${answered_by_html_id}`).value;
            let confirmed_by = document.querySelector(`#${confirmed_by_html_id}`).value;
            
            alert("Assigned Successfully")

            //POST the assigned theras to answer and confirm
            fetch('/assign/fetch', {
                method: 'POST',
                body: JSON.stringify({
                    answered_by: answered_by,
                    confirmed_by: confirmed_by,
                    box_id: box_id
                })
            })
        }
    });
})
