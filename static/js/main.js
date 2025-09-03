document.addEventListener('DOMContentLoaded', function() {
    // 更新服务器状态
    function updateServerStatus() {
        // 获取所有服务器状态元素
        const statusElements = document.querySelectorAll('[data-server-id]');
        statusElements.forEach(element => {
            const serverId = element.getAttribute('data-server-id');
            fetch(`/api/server_status/${serverId}`)
                .then(response => response.json())
                .then(data => {
                    const statusElement = document.getElementById(`status-${serverId}`);
                    const playersElement = document.getElementById(`players-${serverId}`);
                    if (data.is_online) {
                        statusElement.className = 'server-status status-online';
                        statusElement.textContent = '在线';
                    } else {
                        statusElement.className = 'server-status status-offline';
                        statusElement.textContent = '离线';
                    }
                    playersElement.textContent = `${data.current_players}/${data.max_players}`;
                })
                .catch(error => {
                    console.error('Error updating server status:', error);
                });
        });
    }
    // 每30秒更新一次服务器状态
    setInterval(updateServerStatus, 10000);

    // 页面加载时立即更新一次
    updateServerStatus();

    // 删除确认
    const deleteButtons = document.querySelectorAll('.btn-delete');
    deleteButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            if (!confirm('确定要删除吗？此操作不可恢复！')) {
                e.preventDefault();
            }
        });
    });
});