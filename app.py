from flask import Flask, render_template, jsonify
import docker
import time
from datetime import datetime, timezone

app = Flask(__name__)


# ─── Docker Client ────────────────────────────────────────────────────────────

def get_docker_client():
    """
    Connect to the Docker daemon via the mounted socket.
    /var/run/docker.sock is mounted from the host into this container.
    This gives us the same access as running docker commands on zeus01 directly.
    """
    try:
        client = docker.from_env()
        client.ping()  # verify daemon is reachable
        return client, None
    except docker.errors.DockerException as e:
        return None, str(e)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def get_cpu_percent(container):
    """
    CPU percentage requires two stat samples with a delta calculation.
    The Docker stats API returns cumulative CPU nanoseconds, not a percentage.
    We take two readings 0.1s apart and calculate the delta.

    Interview answer: "Docker reports cumulative CPU usage. To get a percentage
    you calculate the delta between two readings divided by the system CPU delta,
    multiplied by the number of CPUs."
    """
    try:
        stats1 = container.stats(stream=False)
        time.sleep(0.1)
        stats2 = container.stats(stream=False)

        cpu_delta = (
            stats2['cpu_stats']['cpu_usage']['total_usage'] -
            stats1['cpu_stats']['cpu_usage']['total_usage']
        )
        system_delta = (
            stats2['cpu_stats']['system_cpu_usage'] -
            stats1['cpu_stats']['system_cpu_usage']
        )
        num_cpus = stats2['cpu_stats'].get('online_cpus', 1)

        if system_delta > 0:
            return round((cpu_delta / system_delta) * num_cpus * 100, 2)
        return 0.0
    except Exception:
        return None


def get_memory_stats(container):
    """
    Memory usage and limit from a single stats call.
    Returns used MB and limit MB.
    """
    try:
        stats = container.stats(stream=False)
        mem_stats = stats.get('memory_stats', {})
        usage = mem_stats.get('usage', 0)
        limit = mem_stats.get('limit', 0)

        # Subtract cache from usage (Linux reports cache as used memory)
        cache = mem_stats.get('stats', {}).get('cache', 0)
        actual_usage = max(0, usage - cache)

        return {
            'used_mb': round(actual_usage / (1024 * 1024), 1),
            'limit_mb': round(limit / (1024 * 1024), 1),
            'percent': round((actual_usage / limit * 100), 1) if limit > 0 else 0
        }
    except Exception:
        return {'used_mb': 0, 'limit_mb': 0, 'percent': 0}


def format_uptime(started_at_str):
    """
    Convert Docker's started_at timestamp to a human-readable uptime string.
    e.g. "2h 34m" or "3d 12h"
    """
    try:
        # Docker returns ISO format with timezone
        started = datetime.fromisoformat(started_at_str.replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        delta = now - started
        total_seconds = int(delta.total_seconds())

        days = total_seconds // 86400
        hours = (total_seconds % 86400) // 3600
        minutes = (total_seconds % 3600) // 60

        if days > 0:
            return f"{days}d {hours}h"
        elif hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"
    except Exception:
        return 'unknown'


def get_container_data(client):
    """
    Collect data for all containers — running and stopped.
    Returns two lists: running and stopped.
    """
    running = []
    stopped = []

    try:
        all_containers = client.containers.list(all=True)
    except docker.errors.DockerException:
        return [], []

    for container in all_containers:
        # Get port mappings
        ports = []
        port_bindings = container.ports or {}
        for container_port, host_bindings in port_bindings.items():
            if host_bindings:
                for binding in host_bindings:
                    host_port = binding.get('HostPort', '')
                    if host_port:
                        ports.append({
                            'host': host_port,
                            'container': container_port.replace('/tcp', '').replace('/udp', '')
                        })

        # Get image info
        try:
            image = client.images.get(container.image.id)
            image_size_mb = round(image.attrs.get('Size', 0) / (1024 * 1024), 1)
            image_name = container.image.tags[0] if container.image.tags else container.image.short_id
        except Exception:
            image_size_mb = 0
            image_name = 'unknown'

        # Get logs
        try:
            logs = container.logs(tail=20).decode('utf-8', errors='replace').strip()
            log_lines = logs.split('\n') if logs else []
        except Exception:
            log_lines = []

        data = {
            'id': container.short_id,
            'name': container.name,
            'status': container.status,
            'image': image_name,
            'image_size_mb': image_size_mb,
            'ports': ports,
            'log_lines': log_lines,
        }

        if container.status == 'running':
            attrs = container.attrs.get('State', {})
            started_at = attrs.get('StartedAt', '')
            data['uptime'] = format_uptime(started_at)
            data['cpu_percent'] = get_cpu_percent(container)
            data['memory'] = get_memory_stats(container)
            running.append(data)
        else:
            data['uptime'] = '—'
            data['cpu_percent'] = None
            data['memory'] = None
            stopped.append(data)

    return running, stopped


def get_docker_info(client):
    """
    Host-level Docker info — version, total containers, images.
    """
    try:
        info = client.info()
        version = client.version()
        return {
            'docker_version': version.get('Version', 'unknown'),
            'containers_running': info.get('ContainersRunning', 0),
            'containers_stopped': info.get('ContainersStopped', 0),
            'images': info.get('Images', 0),
            'host': info.get('Name', 'unknown'),
        }
    except Exception:
        return {}


def get_network_info(client):
    """
    List Docker networks — demonstrates network awareness.
    """
    try:
        networks = client.networks.list()
        result = []
        for net in networks:
            # Skip default Docker networks that aren't interesting
            if net.name in ['none', 'host']:
                continue
            containers_on_net = len(net.attrs.get('Containers', {}))
            result.append({
                'name': net.name,
                'driver': net.attrs.get('Driver', 'unknown'),
                'containers': containers_on_net,
            })
        return result
    except Exception:
        return []


# ─── Routes ──────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    client, error = get_docker_client()

    if error:
        return render_template('error.html', message=error)

    running, stopped = get_container_data(client)
    docker_info = get_docker_info(client)
    networks = get_network_info(client)

    return render_template('index.html',
        running=running,
        stopped=stopped,
        docker_info=docker_info,
        networks=networks,
        last_updated=datetime.now().strftime('%H:%M:%S'),
        refresh_interval=30
    )


@app.route('/health')
def health():
    """Simple health check endpoint."""
    client, error = get_docker_client()
    if error:
        return jsonify({'status': 'error', 'message': error}), 500
    return jsonify({'status': 'ok', 'timestamp': datetime.now().isoformat()})


# ─── Init ────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
