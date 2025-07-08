<template>
    <div class="header-time">北京时间：{{ currentTime }}</div>
</template>

<script>
export default {
    data() {
        return {
            currentTime: ""
        };
    },
    mounted() {
        this.updateTime();
        this.timer = setInterval(this.updateTime, 1000);
    },
    beforeDestroy() {
        clearInterval(this.timer);
    },
    methods: {
        updateTime() {
            const now = new Date();
            this.currentTime = now.toLocaleString();
        }
    }
};
</script>

<style scoped>
.header-time {
    font-size: 28px;
    font-weight: bold;
    color: #333;
    text-align: center;
    margin-bottom: 10px;
}
</style>