document.getElementById('createBoardBtn').addEventListener('click', () => {
    document.getElementById('createBoardModal').classList.add('active');
    document.getElementById('modalOverlay').classList.add('active');
});

document.getElementById('closeCreateBoardBtn').addEventListener('click', () => {
    document.getElementById('createBoardModal').classList.remove('active');
    document.getElementById('modalOverlay').classList.remove('active');
});

document.getElementById('modalOverlay').addEventListener('click', () => {
    document.getElementById('createBoardModal').classList.remove('active');
    document.getElementById('modalOverlay').classList.remove('active');
});

document.getElementById('openBoardBtn').addEventListener('click', () => {
    document.getElementById('existingBoardsModal').classList.add('active');
    document.getElementById('modalOverlay').classList.add('active');
});

document.getElementById('closeExistingBoardsBtn').addEventListener('click', () => {
    document.getElementById('existingBoardsModal').classList.remove('active');
    document.getElementById('modalOverlay').classList.remove('active');
});



function getMemberEmails() {
    const memberEmails = [];
    const memberInputs = document.querySelectorAll('#membersList .member-email');
    
    // Loop through each input field and get the value
    memberInputs.forEach(input => {
        const email = input.value.trim();
        if (email) {
            memberEmails.push(email); // Only add non-empty values
        }
    });
    
    return memberEmails;
}

document.addEventListener('DOMContentLoaded', () => {
    const membersList = document.getElementById('membersList');
    const addMemberBtn = document.getElementById('addMemberBtn');

    // Add a new member input field
    addMemberBtn.addEventListener('click', () => {
        const memberItem = document.createElement('div');
        memberItem.classList.add('member-item');
        memberItem.innerHTML = `
            <input type="email" name="boardMembers[]" class="member-email" placeholder="Enter member email" required>
            <button type="button" class="remove-member-btn">Remove</button>
        `;
        membersList.appendChild(memberItem);
    });

    // Remove a member input field
    membersList.addEventListener('click', (event) => {
        if (event.target.classList.contains('remove-member-btn')) {
            const memberItem = event.target.parentElement;
            membersList.removeChild(memberItem);
        }
    });


    document.getElementById('saveBoardBtn').addEventListener('click', () => {
        var boardName = document.getElementById('boardName').value;
        var boardDescription = document.getElementById('boardDescription').value;
        var membersList = getMemberEmails();
    
        // Check for empty inputs (basic client-side validation)
        if (!boardName || !boardDescription) {
            alert('Both fields are required.');
            return;
        }
    
        // AJAX request to send data to the /createtable route
        $.ajax({
            url: '/create_board', // Replace with your Flask route URL
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                name: boardName,
                description: boardDescription,
                members: membersList
            }),
            success: function (response) {
                if (response.success) {
                    alert('Table created successfully!');
                    $('#createBoardModal').removeClass('active');
                    $('#modalOverlay').removeClass('active');
                    // Optionally, update the UI with the new table
                    const $userBoardsList = $('#userBoardsList');
                    $userBoardsList.empty(); // Clear existing list

                    response.boards.forEach(board => {
                        const $listItem = $(`<li><a href="/view_board/${board.board_id}">${board.name}</a></li>`);
                        $userBoardsList.append($listItem);
                    });
                } else {
                    alert('Failed to create table: ' + response.message);
                }
            },
            error: function (xhr, status, error) {
                alert('An error occurred: ' + error);
            }
        });
    });
});