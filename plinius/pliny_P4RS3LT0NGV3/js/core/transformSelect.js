/**
 * Shared transform picker dropdown (category optgroups + favorites).
 * Used by Splitter, Universal Decoder, and any tool that picks a transform.
 */
(function(global) {
    'use strict';

    function transformSelectFilter(root, decodableOnly) {
        const list = (root && root.transforms) ? root.transforms : [];
        if (!decodableOnly) return list;
        return list.filter(function(t) {
            return t && typeof t.reverse === 'function' && t.name !== 'Random Mix';
        });
    }

    function transformSelectFavorites(root, decodableOnly) {
        const favorites = (root && root.favorites) ? root.favorites : [];
        const pool = transformSelectFilter(root, decodableOnly);
        return favorites
            .filter(function(f) { return typeof f === 'string'; })
            .map(function(name) { return pool.find(function(t) { return t.name === name; }); })
            .filter(Boolean);
    }

    function transformSelectByCategory(root, category, decodableOnly) {
        const pool = transformSelectFilter(root, decodableOnly);
        const list = pool.filter(function(t) { return t.category === category; });
        const favorites = (root && root.favorites) ? root.favorites : [];
        if (!favorites.length) return list;
        return list.filter(function(t) {
            return !favorites.some(function(f) { return typeof f === 'string' && f === t.name; });
        });
    }

    function transformSelectCategoryOrder(root) {
        if (root && Array.isArray(root.categories) && root.categories.length) {
            return root.categories;
        }
        const pool = transformSelectFilter(root, false);
        const set = new Set();
        pool.forEach(function(t) {
            if (t.category) set.add(t.category);
        });
        const cats = Array.from(set).filter(function(c) { return c !== 'randomizer'; }).sort();
        if (set.has('randomizer')) cats.push('randomizer');
        return cats;
    }

    function transformSelectCategoryLabel(category) {
        if (!category) return '';
        return category.charAt(0).toUpperCase() + category.slice(1);
    }

    function registerTransformSelectComponent(Vue) {
        Vue.component('transform-select', {
            props: {
                value: { type: String, default: '' },
                decodableOnly: { type: Boolean, default: false },
                includeAuto: { type: Boolean, default: false },
                showEmpty: { type: Boolean, default: false },
                emptyLabel: { type: String, default: 'None' },
                selectClass: { type: [String, Object, Array], default: 'transform-select' }
            },
            computed: {
                categoryOrder: function() {
                    return transformSelectCategoryOrder(this.$root);
                },
                favoriteTransforms: function() {
                    return transformSelectFavorites(this.$root, this.decodableOnly);
                },
                visibleCategories: function() {
                    var self = this;
                    return this.categoryOrder.filter(function(category) {
                        return self.transformsForCategory(category).length > 0;
                    });
                }
            },
            methods: {
                categoryDisplayName: function(category) {
                    return transformSelectCategoryLabel(category);
                },
                transformsForCategory: function(category) {
                    return transformSelectByCategory(this.$root, category, this.decodableOnly);
                },
                onChange: function(event) {
                    this.$emit('input', event.target.value);
                    this.$emit('change', event);
                }
            },
            template: '\
<select \
    :value="value" \
    @change="onChange" \
    :class="selectClass"> \
    <option v-if="showEmpty" value="">{{ emptyLabel }}</option> \
    <option v-if="includeAuto" value="auto">&#128269; Auto-detect</option> \
    <optgroup v-if="favoriteTransforms.length > 0" label="&#11088; Favorites"> \
        <option v-for="t in favoriteTransforms" :key="\'f-\' + t.name" :value="t.name">{{ t.name }}</option> \
    </optgroup> \
    <optgroup \
        v-for="category in visibleCategories" \
        :key="category" \
        :label="categoryDisplayName(category)"> \
        <option \
            v-for="t in transformsForCategory(category)" \
            :key="t.name" \
            :value="t.name">{{ t.name }}</option> \
    </optgroup> \
</select>'
        });
    }

    global.transformSelectFilter = transformSelectFilter;
    global.transformSelectFavorites = transformSelectFavorites;
    global.transformSelectByCategory = transformSelectByCategory;
    global.transformSelectCategoryOrder = transformSelectCategoryOrder;
    global.transformSelectCategoryLabel = transformSelectCategoryLabel;
    global.registerTransformSelectComponent = registerTransformSelectComponent;

    if (typeof Vue !== 'undefined') {
        registerTransformSelectComponent(Vue);
    }
})(typeof window !== 'undefined' ? window : global);
