


/* log of update operations*/
CREATE TABLE IF NOT EXISTS Beekeeper.nodes_log (
    `id`                      INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `node_id`                 VARCHAR(16) NOT NULL ,
    `table_name`              VARCHAR(64),
    `operation`               VARCHAR(64), /* update field, delete row */
    `field_name`              VARCHAR(64),
    `new_value`               VARCHAR(64),
    `source`                  VARCHAR(64), /* who wrote this, node or admin */
    `effective_time`          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `modified_time`           TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX (`effective_time`)
);
/* INSERT ... ON DUPLICATE KEY UPDATE   */
/* sort updates by effective_time, then index */



/* this is derived from nodes_log, do not edit directly */
/* TODO clear separation between info from admin vs info collected from node ! */
/*  id MAC address of the "main" device  */
CREATE TABLE IF NOT EXISTS Beekeeper.nodes_history (
    `id`                    VARCHAR(16) NOT NULL,
    `timestamp`             TIMESTAMP NOT NULL,
    `name`                  VARCHAR(64),
    `project_id`            VARCHAR(64),
    `mode`                  VARCHAR(64),
    `address`               TEXT,
    `position`              POINT SRID 4326,  /* https://dev.mysql.com/doc/refman/8.0/en/gis-wkt-functions.html#function_st-pointfromtext */
    `altitude`              DECIMAL(11, 1), /* or elevation ? sea level or ground ?*/
    `server_node`           VARCHAR(16), /* identifies compute nodes that runs k3s server */
    `internet_connection`   TEXT,  /* optional: instruction how node gets internet access */
    `registration_event`    TIMESTAMP, /* last time (not first!) the node registered (only needed to create a first log entry for node) */
    PRIMARY KEY(`id`, `timestamp`)
);



CREATE TABLE IF NOT EXISTS Beekeeper.sensor_instances (
    `node_id`               VARCHAR(16) NOT NULL,
    `connected_to_type`     VARCHAR(64), /* device, switch, unknown (a sensor is not just connected to a node, but to a certain device)*/
    `connected_to_id`       VARCHAR(64), /* id of above device, switch or nodeid if unknown */
    `sensor_id`             VARCHAR(64), /* reference sensor from table */
    `hardware_id`           VARCHAR(64), /* unique identifer, manufacturer, model etc goes in hardware table*/
    `firmware_version`      VARCHAR(64), 
    `metadata`              TEXT /* anything else? something like this ? https://github.com/waggle-sensor/virtual-waggle/blob/main/data-config.json */
);

CREATE TABLE IF NOT EXISTS Beekeeper.compute_device_instances (
    `id`                    VARCHAR(16) NOT NULL PRIMARY KEY,  /* MAC address !? / TODO Can we add a device without knowing mac address? */
    `node_id`               VARCHAR(16) NOT NULL,
    `vendor`                VARCHAR(64),
    `model`                 VARCHAR(64)
);


CREATE TABLE IF NOT EXISTS Beekeeper.projects (
    `id`                    VARCHAR(16) NOT NULL PRIMARY KEY,
    `name`                  VARCHAR(64),
    `project_id`            VARCHAR(64)
);
