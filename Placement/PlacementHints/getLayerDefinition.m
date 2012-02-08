%%Copyright © BBP/EPFL 2005-2011; All rights reserved. Do not distribute without further notice
function Layer = getLayerDefinition(recipe)
% define Layer Boundaries

xml = xml_read(recipe);

layers = xml.column.layer;
maxLayer = length(layers);
currMin = 0;

for i = maxLayer:-1:1
    Layer(i).From = currMin;
    Layer(i).To = currMin + layers(i).ATTRIBUTE.thickness;
    currMin = Layer(i).To;
end
