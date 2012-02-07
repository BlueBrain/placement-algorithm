classdef XmlSpecifiedRuleCheck < handle
    %XMLSPECIFIEDRULECHECK This class is doing the parsing of placement rules defined
    %in xml format and then checks individual cells.    
    
    properties(Access=private)
        ruleSetFile;
        ruleSets;
        
        morphologyRuleInstances;
        layerInfo;
        
        results;
        
        yBinsSize; %TODO: offer set function
        layerBins;
        transferFcn;
    end
    properties(Access=public)
        strictness;
    end
    
    methods
        function obj = XmlSpecifiedRuleCheck(file,lInfo)
            obj.ruleSetFile = file;
            obj.layerInfo = lInfo;
            obj.yBinsSize = 10; %micron
            obj.transferFcn.id = @(x)x;
            obj.transferFcn.default = @(x)x.^2;
            obj.transferFcn.upper_hard_limit = @(x)obj.upper_hard_limit(x);
            obj.makeLayerBins();
            %then do parsing here            
            xml = parseXML(file);
            obj.addRulesFromXml(xml.Children(cellfun(@(x)x(1)~='#',{xml.Children.Name})));
        end
        function [] = addMorphologyInstance(obj,file)
            %read new rule instances
            if(~exist(file,'file'))
                warning('PlacementHints:ReadRuleInstance:AnnotationsNotFound',...
                    'No annotation xml file found at %s. Adding morphology without constraints',file);
                [~,morphName] = fileparts(file);
                obj.morphologyRuleInstances.(morphName) = [];
            end
            xml =  parseXML(file);            
            ifElseExpansion = @(x,ie)ie{double(x)+1};
            %This relies on lazy evaluation of the if/else condition. If
            %this ever fails just use string returning functions instead of
            %directly returning the string.
            nameFieldLookup = @(x,str,fn)ifElseExpansion(any(cellfun(@(s)strcmp(s,str),{x.Name})),{'',x(cellfun(@(s)strcmp(s,str),{x.Name})).(fn)});
            if(isempty(xml.Attributes))
                warning('PlacementHints:ReadRuleInstance:MorphologyNotSpecified','Morphology name not specified in xml. Guessing from filename: %s',file);
                [~,morphName] = fileparts(file);
            else
                morphName = nameFieldLookup(xml.Attributes,'morphology','Value');
            end
            annotations = xml.Children;
            annotations = annotations(cellfun(@(x)strcmp(x,'placement'),{annotations.Name}));
            for i = 1:length(annotations)
                instance = nameFieldLookup(annotations(i).Children,'use_rule','Attributes');
                ruleName = nameFieldLookup(instance,'rule','Value');
                %Right now we only consider y intervals. Any other cases
                %planned?
                y_min = str2double(nameFieldLookup(instance,'y_min','Value'));
                y_max = str2double(nameFieldLookup(instance,'y_max','Value'));
                obj.morphologyRuleInstances.(morphName)(i).Rule = ruleName;
                obj.morphologyRuleInstances.(morphName)(i).Interval = [y_min y_max];
            end            
        end
        function scores = getResult(obj,morphName,inLayer,asMType)            
            scores = obj.checkMorphology(morphName,inLayer,asMType);            
            obj.results(end+1).morphology = morphName;
            obj.results(end).mtype = asMType;
            obj.results(end).scores = scores;
            obj.results(end).layer = inLayer;
        end
        function [] = plotOverview(obj,varargin)
            filter = ones(1,size(obj.results));
            titleStr = '';
            for i = 1:2:length(varargin)
                if(ischar(varargin{i+1}))
                    filter = filter.*cellfun(@(x)strcmp(x,varargin{i+1}),{obj.results.(varargin{i})});
                    titleStr = cat(2,titleStr,sprintf('%s is %s; ',varargin{i:i+1}));
                else
                    filter = filter.*(obj.results.(varargin{i})==varargin{i+1});
                    titleStr = cat(2,titleStr,sprintf('%s is %d; ',varargin{i:i+1}));
                end                 
            end
            valids = obj.results(find(filter));
            allYBins = catCell(2,obj.layerBins([valids.layer]));
            allScores = catCell(2,{obj.results.scores});
            figure('Position',[200 300 300 800]);
            boxplot(allScores,allYBins,'plotstyle','compact','orientation','horizontal');
            axes('Position',get(gca,'Position'),'Color','none','XTick',[],'YTick',[]);
            line(cellfun(@(y)sum(allScores(allYBins==y)),num2cell(unique(allYBins))),unique(allYBins),'Color',[1 0 0]);
            xlabel('score');ylabel('\mum');            
        end
        function [] = writeChampions(obj,toFile)
            fid = fopen(toFile,'w');
            layerMType = cellfun(@(x,y)sprintf('Layer %d: %s',x,y),{obj.results.layer},{obj.results.mtype},'UniformOutput',false);
            umtype = unique(layerMType);
            for i = 1:length(umtype)
                fprintf(fid,'For mtype = %s\n',umtype{i});
                indices = find(cellfun(@(x)strcmp(x,umtype{i}),layerMType));                
                bins = obj.layerBins{obj.results(indices(1)).layer};
                for j = 1:length(bins)
                    [scores sorted] = sort(cellfun(@(x)x(j),{obj.results(indices).scores}));
                    for k = length(scores)+[0 -1 -2]
                        fprintf(fid,'\t%s: %d\n',obj.results(indices(sorted(k))).morphology,scores(k));
                    end
                end                
            end
            fclose(fid);
        end
        
    end
    methods(Access=private)        
        function scores = checkMorphology(obj,morphName,inLayer,asMType)
            if(~isfield(obj.morphologyRuleInstances,morphName))
                error('PlacementHints:getResults:MorphologyNotAnnotated','Morphology %s has no rule instance file specified!',morphName);
            else
                if(~isfield(obj.ruleSets,asMType))
                    error('PlacementHints:getResults:MTypeNotKnown','Cannot find rules for MType %s!',asMType);
                end
                relevantInstances = obj.morphologyRuleInstances.(morphName);
                relevantRuleSet = obj.ruleSets.(asMType); 
                scores = ones(0,length(obj.layerBins{inLayer}));
                for i = 1:length(relevantInstances)
                    scores(i,:) = obj.checkRuleInstance(relevantInstances(i),relevantRuleSet,obj.layerBins{inLayer});
                end
                scores = mergeScores(scores);
            end
        end
        function scores = checkRuleInstance(obj,instance,set,bins)
            if(~isfield(set,instance.Rule))
                error('PlacementHints:getResults:UnknownRule','Rule instance refers to rule %s in %s, which is not defined!',...
                    instance.Rule,set.mtype);
            end
            minMaxFcn = @(x,y)cat(2,max(x(1),y(1)),min(x(2),y(2)));
            intervalAbs = obj.getLayerInterval(set.(instance.Rule));            
            scores = cellfun(@(x)diff(minMaxFcn(intervalAbs,instance.Interval+x)),num2cell(bins))./min(diff(intervalAbs),diff(instance.Interval));
            scores(scores<0)=0;
            if(isfield(instance,'transferFcn'))
                scores = obj.transferFcn.(strrep(instance.transferFcn,'-','_'))(scores);
            else
                scores = obj.transferFcn.default(scores);
            end
        end
        function scores = mergeScores(obj,scores)  
            if(isempty(scores))
                scores = ones(1,size(scores,2));
                return;
            end
            fcn = @(x,p)((sum(x.^p)/length(x))^(1/p));
            shapeParameter = norminv(obj.strictness/101,1,2.25);            
            baseWeight = size(scores,1).*(log10(obj.strictness).^10);
            scores = round(baseWeight.*cellfun(@(x)fcn(x,shapeParameter),num2cell(scores,1))+ones(1,size(scores,2)));
        end
        
        %Function subject to change if we ever inplement more than just y
        %intervals. For now lazily implemented
        function interval = getLayerInterval(obj,rule)
            fractionLookup = @(iv,f)iv(1)+f*diff(iv);
            getIv = @(x)cat(2,obj.layerInfo(x).From,obj.layerInfo(x).To);
            
            l = cat(1,str2double(rule.y_min_layer), str2double(rule.y_max_layer));
            f = cat(1,str2double(rule.y_min_fraction), str2double(rule.y_max_fraction));
            interval = cat(2,fractionLookup(getIv(l(1)),f(1)),fractionLookup(getIv(l(2)),f(2)));
        end                      
        
        function [] = addRulesFromXml(obj,xml)
            ifElseExpansion = @(x,ie)ie{double(x)+1};
            %This relies on lazy evaluation of the if/else condition. If
            %this ever fails just use string returning functions instead of
            %directly returning the string.
            nameValueLookup = @(x,str)ifElseExpansion(any(cellfun(@(s)strcmp(s,str),{x.Name})),{'',x(cellfun(@(s)strcmp(s,str),{x.Name})).Value});
            
            for i = 1:length(xml)
                currMType = nameValueLookup(xml(i).Attributes,'mtype');
                obj.ruleSets.(currMType).mtype = currMType;
                %If we ever have other types of rules add that case here.
                rules = xml(i).Children;
                rules = rules(cellfun(@(x)x(1)~='#',{rules.Name}));
                for j = 1:length(rules)
                    id = nameValueLookup(rules(j).Attributes,'id');
                    if(isempty(id))
                        error('XMLPlacementHints:Rules:EmptyIdentifier','This rule has no field "id" specified!');
                    end
                    attr = setdiff({rules(j).Attributes.Name},'id');
                    for k=1:length(attr)
                        obj.ruleSets.(currMType).(id).(attr{k}) = nameValueLookup(rules(j).Attributes,attr{k});
                    end
                end
            end
        end
        
        function [] = makeLayerBins(obj)            
            for i = 1:length(obj.layerInfo)
                borders = linspace(obj.layerInfo(i).From,obj.layerInfo(i).To,...
                    ceil((obj.layerInfo(i).To-obj.layerInfo(i).From)/obj.yBinsSize)+1);
                obj.layerBins{i} = (borders(1:end-1) + borders(2:end))./2;
            end
        end
    end
    
    
    methods(Static=true)
        %Implement transfer functions here
        function dat = upper_hard_limit(dat)
            dat(find(dat(2:end)<dat(1:end-1))+1)=0;
        end
    end
end

