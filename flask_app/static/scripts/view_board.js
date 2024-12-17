var socket;
var board;
var listToAdd;
var lockedCards = [];

document.addEventListener('DOMContentLoaded', () => {
    socket = io.connect(window.href);
    socket.on('connect', function() {
        var parts = window.location.href.split('/');
        var board_id = parts[parts.length - 1];
        socket.emit('join_board', {board_id: board_id});socket.emit('joined', {});
    });

    socket.on('current_board', (data) => {
        board = data.board;
    });

    socket.on('new_card', (data) => {
        addNewCard(data.card, data.list_id);
    });

    socket.on('receive_lock', (data) => {
        lockedCards = data;
    });

    socket.on('card_edited', (data) => {
        console.log(data);
        idEdited = "card_" + data.card_id;
        $(`#${idEdited}`).find('.card-description').val(data.description);
    });

    socket.on('card_deleted', (data) => {
        deleteId = "card_" + data.card_id;
        const card = $(`#${deleteId}`).closest('.card'); // Find the closest card container

        // Remove the card from the DOM
        card.remove();

        // Ensure empty lists are valid drop targets
        $(".list-items").each(function () {
            if ($(this).children().length === 0) {
                $(this).addClass("empty-list");
            }
        });
    });

    socket.on('card_moved', (data) => {
        const { card_id, new_list, new_position } = data;

        // Find the card element by its ID
        const card = $(`#card_${card_id}`);

        // Check if the card exists in the DOM
        if (card.length === 0) {
            console.error(`Card with ID ${card_id} not found in the DOM`);
            return;
        }

        // Find the target list container
        const targetList = $(`#list_${new_list} .list-items`);

        // Check if the target list exists in the DOM
        if (targetList.length === 0) {
            console.error(`Target list with ID list_${new_list} not found in the DOM`);
            return;
        }

        // Remove the card from its current list and append it to the new list
        card.detach().appendTo(targetList);

        // Reposition the card within the new list
        if (new_position >= 0 && new_position < targetList.children().length) {
            const targetCard = targetList.children().eq(new_position);
            card.insertBefore(targetCard);
        } else {
            // If the position is out of bounds, append the card to the end
            targetList.append(card);
        }

        // Ensure empty lists are valid drop targets
        $(".list-items").each(function () {
            if ($(this).children().length === 0) {
                $(this).addClass("empty-list");
            }
        });

        console.log(
            `Card with ID ${card_id} moved to list ${new_list} at position ${new_position}`
        );
    });


     // Enable sortable functionality for all list-items containers
    $(".list-items").sortable({
        connectWith: ".list-items", // Allow movement between lists
        placeholder: "sortable-placeholder", // Class for the placeholder
        forcePlaceholderSize: true, // Ensure placeholder appears in empty lists
        tolerance: "pointer", // Improves dragging experience
        start: function (event, ui) {
            // Style the placeholder when dragging starts
            ui.placeholder.height(ui.helper.outerHeight());
            ui.placeholder.width(ui.helper.outerWidth());
        },
        stop: function (event, ui) {
            const card = ui.item; // The dragged card
            var cardId = card.attr("id");
            cardId = cardId.substring(5, cardId.length);
            const newListId = card.closest(".list").attr("id").replace("list_", "");
            const newPosition = card.index(); // Get the new position within the list

            // Ensure empty lists are valid drop targets
            $(".list-items").each(function () {
                if ($(this).children().length === 0) {
                    $(this).addClass("empty-list");
                }
            });

            console.log(
                `Card ${cardId} to list ${newListId} at position ${newPosition}`
            );

            //Handle backend sync or UI updates here
            socket.emit('card_moved', {
                card_id: cardId,
                new_list: newListId,
                new_position: newPosition,
                room: board.board_id
            });
        },
    }).disableSelection();

    // Ensure empty lists are valid drop targets
    $(".list-items").each(function () {
        if ($(this).children().length === 0) {
            $(this).addClass("empty-list");
        }
    });

    $(document).on("sortreceive", function (event, ui) {
        const targetList = $(event.target);

        // Remove empty list class when a card is dropped
        if (targetList.hasClass("empty-list")) {
            //targetList.removeClass("empty-list");
        }
    });

});



$('.add-card-btn').click(function(){
    
    document.getElementById('createCardModal').classList.add('active');
    document.getElementById('modalOverlay').classList.add('active');
    listToAdd = $(this).closest('.list').attr('id');
    listToAdd = listToAdd.substring(5, listToAdd.length);

});

$('#closeCreateCardBtn').click(() => {
    document.getElementById('createCardModal').classList.remove('active');
    document.getElementById('modalOverlay').classList.remove('active');
});

$(document).on('click', '.delete-card-btn', function() {
    const card = $(this).closest('.card'); // Find the closest card container
    
    var cardId = card.attr('id'); // Get the card's ID for reference
    cardId = cardId.substring(5, cardId.length);

    // Remove the card from the DOM
    card.remove();

    // Ensure empty lists are valid drop targets
    $(".list-items").each(function () {
        if ($(this).children().length === 0) {
            $(this).addClass("empty-list");
        }
    });


    // emit to the server that we deleted a card
    socket.emit('delete_card', {
        card_id: cardId,
        room:board.board_id
    });
});

$(document).on('click', '.edit-card-btn', function () {

    const card = $(this).closest('.card'); // Find the closest card container
    const descriptionInput = card.find('.card-description'); // Find the input element
    const editButton = $(this); // The clicked button
    var thisId = card.attr('id');
    thisId = thisId.substring(5, thisId.length);
    // Toggle between Edit and Save
    if (editButton.text() === 'Edit') {
        console.log(lockedCards)
        // check if this is locked 
        if (lockedCards.includes(thisId)) {
            alert(`Card ${card.find('.card-title').text()} is locked.`);
            return;
        }
        editButton.text('Save'); // Change button text to Save
        descriptionInput.removeAttr("disabled");
    } else {
        editButton.text('Edit'); // Change button text back to Edit
        descriptionInput.prop('disabled', true); // Disable the input

        // emit the new text
        socket.emit('edit_card', {
            card_id: thisId,
            room: board.board_id,
            description: descriptionInput.val()
        });
    }

    // Emit a socket event to lock this card. This toggles lock/unlocked
    socket.emit('toggle_card', {
        card_id: thisId,
        room: board.board_id
    });
});


$('#closeSaveCardBtn').click(() => {
    let title = $("#cardTitle").val();
    let description = $("#cardDescription").val();
    var position = 0;

    //this code finds the greatest position of the cards. We are adding to the end.
    board.lists.forEach(l => {
        if (l.list_id === parseInt(listToAdd)) {//check to see this is the right list.
            let max = 0;
            if (l.cards.length > 0) {//if it's empty, assign this card to position 0, otherwise max + 1
                l.cards.forEach(card => {
                    if (card.position > max)
                    {
                        max = card.position;
                    }
                });
                position = max + 1;
            } else {
                position = 0;
            }
        }
    });

    socket.emit('create_card', {card: {title: title, description: description, position: position}, 
        list_id: listToAdd, room: board.board_id});

    document.getElementById('createCardModal').classList.remove('active');
    document.getElementById('modalOverlay').classList.remove('active');
});


function addNewCard(card, list_id)
{
    // Create a jQuery object for the card
    const cardElement = $(`
        <div class="card" id="card_${card.card_id}">
            <div class="card-content">
                <h3 class="card-title">${card.title}</h3>
                <input type="text" value="${card.description}" disabled class="card-description">
            </div>
            <div class="card-actions">
                <button class="edit-card-btn">Edit</button>
                <button class="delete-card-btn">Delete</button>
            </div>
        </div>
    `);

    var listContainer = $(`#list_${list_id} .list-items`);

    if (listContainer.length === 0) {
        console.error(`List with ID ${list_id} not found`);
        //return;
    }

    listContainer.append(cardElement);
}


//cse477-fall-2024-434018
//gcloud builds submit --tag gcr.io/cse477-fall-2024-434018/exam
//gcloud run deploy --image gcr.io/cse477-fall-2024-434018/exam --platform managed --memory 4Gi


document.addEventListener('DOMContentLoaded', () => {
    const chatWindow = document.getElementById('chatWindow');
    const chatInput = document.getElementById('chatInput');
    const sendChatBtn = document.getElementById('sendChatBtn');

    // Send Chat Message
    sendChatBtn.addEventListener('click', () => {
        const message = chatInput.value.trim();
        if (message) {
            socket.emit('out_message', {
                msg: message,
                room: board.board_id
            });
            chatInput.value = ''; // Clear the input field
        }
    });

    // Press Enter to Send
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendChatBtn.click();
        }
    });

    // Receive Chat Messages
    socket.on('in_message', (data) => {
        const messageElement = document.createElement('div');
        messageElement.textContent = `${data.user}: ${data.msg}`;
        messageElement.className = 'chat-message';
        chatWindow.appendChild(messageElement);

        // Auto-scroll to the latest message
        chatWindow.scrollTop = chatWindow.scrollHeight;
    });

});
